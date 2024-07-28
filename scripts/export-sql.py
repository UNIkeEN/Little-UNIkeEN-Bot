import argparse
import subprocess
import json
import datetime

if __name__ == '__main__':
    parser = argparse.ArgumentParser("export bot sql to file")
    parser.add_argument('config', type=str, help='path to config.json')
    parser.add_argument('-o', '--output', type=str, help='path to output file', 
                        required=False, default=datetime.datetime.now().strftime('BOTDATA_%y%m%d.sql'))
    parser.add_argument('--clear-file-record', action='store_true', 
                        help='if trigger, then clear all file record binary, make the exporting lightweight and fast',
                        default=False)
    args = parser.parse_args()
    outFile = args.output
    print('write output to %s'%outFile)
    with open(args.config, 'r') as f:
        config = json.load(f)
    sqlConfig = config['sql']
    qq = config['qq']
    databases = ['BOT_DATA_%d'%qq, 'BOT_FAQ_DATA']
    cmd = [ 'mysqldump',
            '-u', sqlConfig['user'],
            '-p%s'%sqlConfig['passwd'],
            '--databases', *databases]
    # print(cmd)
    if args.clear_file_record:
        import mysql.connector
        mydb = mysql.connector.connect(**sqlConfig)
        mycursor = mydb.cursor()
        mydb.autocommit = True
        print('clear file record binaries...', end='')
        mycursor.execute("""
        UPDATE `BOT_DATA_%d`.`fileRecord` SET `file_bin` = NULL
        """%qq)
        print('  done')
    print('exporting...', end='')  
    with open(outFile, 'w') as f:
        popen = subprocess.Popen(cmd, stdout=f)
        out,err = popen.communicate()
        if popen.returncode == 0:
            print('  done')
        else:
            print('  error, not return 0')