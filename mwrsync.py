#!/usr/bin/env python

import socket
import sys
import json
import inspect
import os


import webrepl_cli
import darp
from gitignore_parser import parse_gitignore


def send_raw_cmd(ws, cmd, verbose=False):
  ws.write(b"\x05A\x01", webrepl_cli.WEBREPL_FRAME_TXT)
  read_until(ws, b"R\x01\x80\x00\x01")

  cmd = cmd
  if verbose: print(cmd)
  for c in [cmd[i:i+256] for i in range(0, len(cmd), 256)]:
    ws.write(c.encode(), webrepl_cli.WEBREPL_FRAME_TXT)
    if len(cmd)>256: read_until(ws, b"\x01")
  ws.write(b'\x04', webrepl_cli.WEBREPL_FRAME_TXT)
  read_until(ws, b"\x04")
  return read_until(ws, b'\x04\x04>')
    
def read_until(ws, s):
  resp = []
  while True:
    c = ws.read(1, text_ok=True)
    resp.append(c)
    if b''.join(resp[-len(s):])==s:
      return b''.join(resp[:-len(s)])

def send_jcmd(ws, cmd):
  cmd = f'print(json.dumps({cmd}))'
  resp = send_raw_cmd(ws, cmd)
  try:
    return json.loads(resp)
  except Exception as e:
    print(e)
    raise Exception(resp)

def _mwrsync_hash_files(prefix='', ret={}):
  import os, binascii, hashlib
  for fn in os.listdir(prefix.rstrip('/')):
    fn = prefix + fn
    st = os.stat(fn)
    if st[0] & 0x4000:
      ret[fn] = '<dir>'
      _mwrsync_hash_files(prefix=fn+'/', ret=ret)
    else:
      hash = hashlib.sha1()
      with open(fn,'rb') as f:
        while data:=f.read(1024):
          hash.update(data)
      ret[fn] = binascii.hexlify(hash.digest())
  return ret

def _mwrsync_hash_files_remote(ws):
  send_raw_cmd(ws, inspect.getsource(_mwrsync_hash_files))
  hashes = send_jcmd(ws, '_mwrsync_hash_files()')
  send_raw_cmd(ws, 'del _mwrsync_hash_files')
  return hashes

def mwrsync(directory, host, port:int=8266, password=None+darp.alt('p'), dry_run:bool=False, verbose:bool=False+darp.alt('v')):

  if not os.path.isdir(directory):
   raise Exception(f'{directory} is not a directory')
  if not directory.endswith('/'):
    directory = directory+'/'

  if ':' in host:
    host, port = host.split(":")
    port = int(port)
  if password is None:
    import getpass
    password = getpass.getpass()  

  if dry_run:
    print('--==[[ dry run ]]==--')
    
  s = socket.socket()
  ai = socket.getaddrinfo(host, port)
  addr = ai[0][4]
  s.connect(addr)
  webrepl_cli.client_handshake(s)
  ws = webrepl_cli.websocket(s)
  webrepl_cli.login(ws, password)
  if verbose:
    print("Remote WebREPL version:", webrepl_cli.get_ver(ws))

  ws.write(b'\r\x01', webrepl_cli.WEBREPL_FRAME_TXT)
  read_until(ws, b'exit\r\n>')
  
  ignore_fn = directory+'.mwrsyncignore'
  if os.path.isfile(ignore_fn):
    ignore = parse_gitignore(ignore_fn)
  else:
    ignore = lambda fn: False

  send_raw_cmd(ws, 'import json, os')

  local = {k[len(directory):]:v for k,v in _mwrsync_hash_files(directory).items()}
  if '.mwrsyncignore' in local:
    del local['.mwrsyncignore']
  #print('local', local)
  remote = _mwrsync_hash_files_remote(ws)
  #print('remote', remote)

  cmds = []
  to_copy = []
  
  for fn, hash in sorted(local.items()):
    if isinstance(hash, bytes): hash = hash.decode()
    if ignore(directory+fn): continue
    #print('comparing', fn, hash, 'to', remote.get(fn))
    if hash!=remote.get(fn):
      if hash=='<dir>':
        cmds.append(f'os.mkdir({repr(fn)})')
      else:
        to_copy.append(fn)
  
  for fn, hash in sorted(remote.items(), reverse=True):
    if ignore(directory+fn): continue
    if fn in local: continue
    if hash=='<dir>':
      cmds.append(f'os.rmdir({repr(fn)})')
    else:
      cmds.append(f'os.remove({repr(fn)})')

  if cmds:
    if dry_run:
      print('would run:\n', '\n '.join(cmds))
    else:
      if verbose: print('running:\n', '\n '.join(cmds))
      send_raw_cmd(ws, '\n'.join(cmds))

  ws.write(b'\x02', webrepl_cli.WEBREPL_FRAME_TXT)
  
  if to_copy and dry_run: print('would copy:')
  for fn in to_copy:
    if dry_run:
      print('', fn)
    else:
      if verbose: print('copying:', fn)
      webrepl_cli.put_file(ws, directory+fn, fn)
  

if __name__=='__main__':
  darp.prep(mwrsync).run()

