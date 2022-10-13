import itertools
from torch.utils import data as dataimport
import re
from time import sleep
import jieba
import torch
import logging
import torch.nn as nn
import torch.nn.functional as F
import torch.nn.utils as utils
from typing import Union, Any
from utils.basicEvent import *
from utils.basicConfigs import *
from utils.functionConfigs import check_config, check_config_mode
from utils.standardPlugin import StandardPlugin
jieba.setLogLevel(logging.INFO) #关闭jieba输出信息

class NLP_Config:
    '''
    数据集相关
    '''
    corpus_data_path = 'resources/corpus/processed.pth' 
    shuffle = True
    load_checkpoint = 'resources/corpus/checkpoint_0827_0938.pth'
    #load_checkpoint = 'NLP/model_save/checkpoint_0821_1253.pth'
    #load_checkpoint = None
    max_input_length = 50 #输入的最大句子长度
    max_generate_length = 20 #生成的最大句子长度
    '''
    训练超参数
    '''
    dim_embedding = 256 # 词嵌入维数
    num_layer = 2 # Encoder-Decoder中RNN的层数
    hidden_size = 256 # 隐藏层大小
    batch_size = 2048
    encoder_lr = 1e-3 # encoder学习率
    decoder_lr = 5e-3 # decoder学习率
    grad_clip = 50.0 # 梯度裁剪
    teacher_forcing_ratio = 1.0 # teacher_forcing的比例
    '''
    训练周期相关
    '''
    num_epoch = 50
    save_epoch = 50
    '''
    设备相关
    '''
    is_cuda = torch.cuda.is_available()
    device = "cuda:0" if is_cuda else "cpu" 

# 模型定义
class Encoder_RNN(nn.Module):
    def __init__(self, conf, len_vocab):
        super(Encoder_RNN, self).__init__()
        # RNN层数与隐藏层大小
        self.num_layer = conf.num_layer
        self.hidden_size = conf.hidden_size
        # emb的输入为字典长度（词的个数）
        self.embedding = nn.Embedding(len_vocab, conf.dim_embedding)
        # 双层GRU
        self.gru = nn.GRU(
            input_size = conf.dim_embedding,
            hidden_size = self.hidden_size,
            num_layers = self.num_layer,
            bidirectional = True # 使用双向GRU
        )

    def forward(self, input_seq, input_lengths, hidden = None): # 初始hidden为空
        '''
        input_seq:输入序列
            size: [max_seq_len, batch_size]
        input_lengths:输入序列长度,某一batch内每个句子的长度列表
            size: [batch_size]
        '''
        # 词嵌入
        embedded = self.embedding(input_seq)
        '''
        embedded:词嵌入处理后
            size: [max_seq_len, batch_size, dim_embedding]
        '''
        # 按照序列长度列表对矩阵进行压缩,加快RNN的计算效率
        packed_data = utils.rnn.pack_padded_sequence(embedded, input_lengths)
        output, hidden = self.gru(packed_data, hidden)
        # 解压缩为定长序列矩阵
        output, _ = utils.rnn.pad_packed_sequence(output)
        '''
        hidden:隐藏层,初始值为None
            size: [num_layers*num_directions, batch_size, hidden_size]
            双向GRU,其第一个维度为不同方向的叠加
        output:输出层
            size: [max_seq_len, batch_size, num_directions*hidden_size]
        '''
        # 对前后两个方向求和输出
        output = output[:,:,:self.hidden_size]+output[:,:,self.hidden_size:]
        '''
        output.size->[max_seq_len, batch_size, hidden_size]
        '''
        return output, hidden
class Decoder_RNN(nn.Module):
    def __init__(self, conf, len_vocab):
        super(Decoder_RNN, self).__init__()
        # RNN层数和隐藏层大小
        self.num_layer = conf.num_layer
        self.hidden_size = conf.hidden_size
        # emb的输入为字典长度（词的个数）
        self.embedding = nn.Embedding(len_vocab, conf.dim_embedding)
        # GRU
        self.gru = nn.GRU(
            input_size = conf.dim_embedding,
            hidden_size = self.hidden_size,
            num_layers = self.num_layer,
        )
        # concat层与输出层
        self.concat = nn.Linear(self.hidden_size*2, self.hidden_size)
        self.out = nn.Linear(self.hidden_size, len_vocab)

    def forward(self, input, hidden, encoder_hiddens):
        '''
        input:输入
            decoder逐字生成,后一个时间步接受前一个时间步生成的字。第一个时间步接受句子开始的符号
            即接受input=开始符索引
            shape:[1, batch_size]
        '''
        # 词嵌入
        embedded = self.embedding(input)
        '''
        embedded:词嵌入处理后
            size: [1, batch_size, dim_embedding]
        '''
        # RNN
        output, hidden = self.gru(embedded, hidden)
        '''
        hidden:隐藏层,最早传入的是encoder最后时刻的输出层,encoder_hidden的正向部分
            size: [num_layers, batch_size, hidden_size]
            双向GRU,其第一个维度为不同方向的叠加
        output:输出层
            size: [max_seq_len, batch_size, hidden_size]
        '''
        # dot方式计算Attention
        '''
        encoder_outputs:
            encoder所有时间步的hidden输出
            shape: [max_seq_len, batch_size, hidden_size]
        '''
        dot_score = torch.sum(output* encoder_hiddens, dim=2).t()
        dot_score = F.softmax(dot_score, dim=1).unsqueeze(1)
        '''
        dot_score: attention的得分
            shape: [max_seq_len, batch_size]
            转置->[batch_size, max_seq_len]
            增加维度->[batch_size, 1, max_seq_len]
        '''
        # 批量相乘，形成context
        context = dot_score.bmm(encoder_hiddens.transpose(0,1))
        context = context.squeeze(1)
        '''
        context:
            shape: [batch_size, hidden_size]
        '''
        output = output.squeeze(0) # [batch_size, hidden_size]
        # 拼接output和context，通过线性层变为单层
        concat_input = torch.cat((output, context), 1)
        concat_output = torch.tanh(self.concat(concat_input)) 
        # 输出与softmax归一化
        final_output = self.out(concat_output)
        final_output = F.softmax(final_output, dim=1)

        return final_output, hidden

class GreedySearchDecoder(nn.Module):
    def __init__(self, encoder, decoder):
        super(GreedySearchDecoder, self).__init__()
        self.encoder = encoder
        self.decoder = decoder

    def forward(self, sos, eos, input_seq, input_length, max_length, device):

        # Encoder的Forward计算 
        encoder_outputs, encoder_hidden = self.encoder(input_seq, input_length)
        # 把Encoder最后时刻的隐状态作为Decoder的初始值
        decoder_hidden = encoder_hidden[:self.decoder.num_layer]
        # 因为我们的函数都是要求(time,batch)，因此即使只有一个数据，也要做出二维的。
        # Decoder的初始输入是SOS
        decoder_input = torch.ones(1, 1, device=device, dtype=torch.long) * sos
        # 用于保存解码结果的tensor
        all_tokens = torch.zeros([0], device=device, dtype=torch.long)
        all_scores = torch.zeros([0], device=device)
        # 循环，这里只使用长度限制，后面处理的时候把EOS去掉了。
        for _ in range(max_length):
            # Decoder forward一步
            decoder_output, decoder_hidden = self.decoder(decoder_input, decoder_hidden, 
								encoder_outputs)
            # decoder_outputs是(batch=1, vob_size)
            # 使用max返回概率最大的词和得分
            decoder_scores, decoder_input = torch.max(decoder_output, dim=1)
            # 把解码结果保存到all_tokens和all_scores里
            all_tokens = torch.cat((all_tokens, decoder_input), dim=0)
            all_scores = torch.cat((all_scores, decoder_scores), dim=0)
            # decoder_input是当前时刻输出的词的ID，这是个一维的向量，因为max会减少一维。
            # 但是decoder要求有一个batch维度，因此用unsqueeze增加batch维度。
            if decoder_input.item() == eos:
                break
            decoder_input = torch.unsqueeze(decoder_input, 0)
            
        # 返回所有的词和得分。
        return all_tokens, all_scores

# data_loader相关
def zipAndPadding(lst, pad):
    ret = itertools.zip_longest(*lst, fillvalue=pad)
    return list(ret)
def maskMatrix(lst, pad):
    mask = []
    for i, seq in enumerate(lst):
        mask.append([])
        for token in seq:
            if token == pad:
                mask[i].append(0)
            else:
                mask[i].append(1)
    return mask
def create_collate_fn(padding, eos):
    '''
    说明dataloader如何包装一个batch,传入的参数为</PAD>的索引padding,</EOS>字符索引eos
    collate_fn传入的参数是由一个batch的__getitem__方法的返回值组成的corpus_item

    corpus_item: 
        lsit, 形如[(inputVar1, targetVar1, index1),(inputVar2, targetVar2, index2),...]
        inputVar1: [word_ix, word_ix, word_ix,...]
        targetVar1: [word_ix, word_ix, word_ix,...]
    inputs: 
        取出所有inputVar组成的list,形如[inputVar1,inputVar2,inputVar3,...], 
        padding后(这里有隐式转置)转为tensor后形状为:[max_seq_len, batch_size]
    targets:
        取出所有targetVar组成的list,形如[targetVar1,targetVar2,targetVar3,...]
        padding后(这里有隐式转置)转为tensor后形状为:[max_seq_len, batch_size]
    input_lengths: 
        在padding前要记录原来的inputVar的长度, 用于pad_packed_sequence
        形如: [length_inputVar1, length_inputVar2, length_inputVar3, ...]
    max_targets_length:
        该批次的所有target的最大长度
    mask:
        形状: [max_seq_len, batch_size]
    indexes:
        记录一个batch中每个 句子对 在corpus数据集中的位置
        形如: [index1, index2, ...]

    '''
    def collate_fn(corpus_item):
        #按照inputVar的长度进行排序,是调用pad_packed_sequence方法的要求
        corpus_item.sort(key=lambda p: len(p[0]), reverse=True) 
        inputs, targets, indexes = zip(*corpus_item)
        input_lengths = torch.tensor([len(inputVar) for inputVar in inputs])
        inputs = zipAndPadding(inputs, padding)
        inputs = torch.LongTensor(inputs) #注意这里要LongTensor
        max_target_length = max([len(targetVar) for targetVar in targets])
        targets = zipAndPadding(targets, padding)
        mask = maskMatrix(targets, padding)
        mask = torch.tensor(mask, dtype=bool)
        targets = torch.LongTensor(targets)
        
        return inputs, targets, mask, input_lengths, max_target_length, indexes

    return collate_fn
class CorpusDataset(dataimport.Dataset):

    def __init__(self, conf):
        self.conf = conf
        self._data = torch.load(conf.corpus_data_path)
        self.word2ix = self._data['word2ix']
        self.corpus = self._data['corpus']
        self.padding = self.word2ix.get(self._data.get('pad'))
        self.eos = self.word2ix.get(self._data.get('eos'))
        self.sos = self.word2ix.get(self._data.get('sos'))
        
    def __getitem__(self, index):
        inputVar = self.corpus[index][0]
        targetVar = self.corpus[index][1]
        return inputVar, targetVar, index

    def __len__(self):
        return len(self.corpus)

def get_dataloader(conf):
    dataset = CorpusDataset(conf)
    dataloader = dataimport.DataLoader(dataset,
                                 batch_size=conf.batch_size,
                                 shuffle=conf.shuffle, #是否打乱数据
                                 drop_last=True, #丢掉最后一个不足一个batch的数据
                                 collate_fn=create_collate_fn(dataset.padding, dataset.eos))
    return dataloader

# 加载模型类
class EvalModel():
    def __init__(self):
        self.load_net()

    def load_net(self):
        self.conf = NLP_Config()
        # 加载数据
        dataloader = get_dataloader(self.conf)
        self._data = dataloader.dataset._data
        self.word2ix, self.ix2word = self._data['word2ix'], self._data['ix2word']
        self.sos = self.word2ix.get(self._data.get('sos'))
        self.eos = self.word2ix.get(self._data.get('eos'))
        self.unk = self.word2ix.get(self._data.get('unk'))
        self.len_vocab = len(self.word2ix)

        self.encoder = Encoder_RNN(self.conf, self.len_vocab)
        self.decoder = Decoder_RNN(self.conf, self.len_vocab)

        checkpoint = torch.load(self.conf.load_checkpoint, map_location='cpu')
        self.encoder.load_state_dict(checkpoint['encoder'])
        self.decoder.load_state_dict(checkpoint['decoder'])

        with torch.no_grad():
            #切换模式
            self.encoder = self.encoder.to(self.conf.device)
            self.decoder = self.decoder.to(self.conf.device)
            self.encoder.eval()
            self.decoder.eval()
            #定义seracher
            self.searcher = GreedySearchDecoder(self.encoder, self.decoder)
    
    def eval(self,input_sentence):
        cop = re.compile("[^\u4e00-\u9fa5^a-z^A-Z^0-9]") #分词处理正则
        input_seq = jieba.lcut(cop.sub("",input_sentence)) #分词序列
        input_seq = input_seq[:self.conf.max_input_length] + ['</EOS>']
        input_seq = [self.word2ix.get(word, self.unk) for word in input_seq]
        tokens = self.generate(input_seq, self.searcher, self.sos, self.eos, self.conf)
        output_words = ''.join([self.ix2word[token.item()] for token in tokens])
        return output_words


    def generate(self, input_seq, searcher, sos, eos, opt):
        #input_seq: 已分词且转为索引的序列
        #input_batch: shape: [1, seq_len] ==> [seq_len,1] (即batch_size=1)
        input_batch = [input_seq]
        input_lengths = torch.tensor([len(seq) for seq in input_batch])
        input_batch = torch.LongTensor([input_seq]).transpose(0,1)
        input_batch = input_batch.to(opt.device)
        input_lengths = input_lengths.to(opt.device)
        tokens, scores = searcher(sos, eos, input_batch, input_lengths, opt.max_generate_length, opt.device)
        return tokens

NLP_model = EvalModel()

class ChatWithNLP(StandardPlugin): # NLP对话插件
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return startswith_in(msg, ['小🦄，','小马，','小🦄,','小马,']) and check_config_mode(data['group_id'],'Auto_Answer')=='nlp'
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        if data['message_type']=='group' and not check_config(data['group_id'],'Auto_Answer'):
            send(data['group_id'],TXT_PERMISSION_DENIED)
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        msg_inp = msg[3:]
        ret = NLP_model.eval(msg_inp)
        ret = ret.replace('</EOS>','',1).replace('</UNK>',' ').strip()
        if ret=="":
            ret = "我好像不明白捏qwq"
        text = f'[CQ:reply,id='+str(data['message_id'])+']'+ret
        send(target, text, data['message_type'])
        sleep(0.3)
        # if ret != "我好像不明白捏qwq":
        #     voice = send_genshin_voice(ret+'。')
        #     send(target, f'[CQ:record,file=files://{ROOT_PATH}/{voice}]', data['message_type'])
        return "OK"
    def getPluginInfo(self, )->Any:
        return {
            'name': 'ChatWithNLP',
            'description': 'NLP对话',
            'commandDescription': '小马，',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }