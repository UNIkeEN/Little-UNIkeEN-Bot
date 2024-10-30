import argparse
import asyncio
import json
import aiohttp
import mysql.connector
import os
from typing import Optional

async def download_file(file_url: str, file_name: str, base_dir: str, verbose:bool=False) -> Optional[int]:
    out_file = os.path.join(base_dir, file_name)
    async with aiohttp.ClientSession() as session:
        async with session.get(file_url, verify_ssl=False) as response:
            if not response.ok:
                return None
            if verbose:
                print('downloading %s to %s'%(file_name, base_dir))
            with open(out_file, 'wb') as f:
                async for chunk in response.content.iter_chunked(4096):
                    f.write(chunk)
            return response.content.total_bytes

if __name__ == '__main__':
    parser = argparse.ArgumentParser("export bot sql to file")
    parser.add_argument('config', type=str, help='path to config.json')
    parser.add_argument('group', type=int, 
                        help='group id, which group\'s files do you want to download')
    parser.add_argument('--outdir', type=str, help='path to output dir', 
                        required=False, default=None)

    args = parser.parse_args()
    outDir = args.outdir
    if outDir is None:
        outDir = os.path.join(os.curdir, str(args.group))
    os.makedirs(outDir, exist_ok=True)
    print('write output to %s'%outDir)
    with open(args.config, 'r') as f:
        config = json.load(f)
    sqlConfig = config['sql']
    qq = config['qq']
    mydb = mysql.connector.connect(**sqlConfig)
    mycursor = mydb.cursor()
    mycursor.execute("""
    SELECT `file_name`, `file_url` from `BOT_DATA_%d`.`fileRecord` where `group_id` = %d
    """%(qq, args.group))
    print('exporting...', )
    loop = asyncio.get_event_loop()
    jobs = []
    for file_name, file_url in list(mycursor):
        # print(file_name, file_url)
        jobs.append(loop.create_task(download_file(file_url, file_name, outDir, verbose=True)))
    loop.run_until_complete(asyncio.wait(jobs))
    print('done.')
    