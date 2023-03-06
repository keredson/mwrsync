# mwrsync
Micropython WebREPL based file sync tool.

This tool will sync your Micropython project directory to your Micropython device over WiFi.  This is much faster than serial, and requires no additional code on the device (since it uses Micropython's built-in WebREPL).

Install
-------
```
pip install mwrsync
```

On your device, [enable WebREPL](https://docs.micropython.org/en/latest/esp8266/tutorial/repl.html?highlight=webrepl#webrepl-a-prompt-over-wifi) by running `import webrepl_setup` or adding this to your `boot.py`:
```
import webrepl
webrepl.start(password='secret')
```

Usage
-----
```
mwrsync <directory> <host>[:<port>] [--port <int>] [-p|--password <value>] [--dry_run] [-v|--verbose]
```

Example: 
```
$ mwrsync esp32/ 10.0.0.128 -v
Password: 
Remote WebREPL version: (1, 19, 1)
copying: test.py
Sent 5 of 5 bytes
```
`--dry-run` will compute changes but not modify the files on the device.  `--verbose` will tell you what it's doing.


Ignoring Files
--------------
Add a file `.mwrsyncignore` to the directory you're syncing.  It follows `.gitignore` syntax.  It will neither copy or delete files that match.

**WARNING:** If you set up WebREPL with `import webrepl_setup`, don't forget to add `webrepl_cfg.py` to `.mwrsyncignore` (or copy it to your project directory). Otherwise you'll disable WebREPL on your next reset.

Speed
-----
On an ESP32 this will hash files at about 272kb/s (on the device).  It will transfer changed files at about 110kb/s.  Most of the time a sync takes me about 4 seconds.

How It Works
------------
This tool will compute a SHA1 hash of your local files, a SHA1 hash of any files on your device, and copy or remove files until the two match.  It only ever modifies files on the device, never locally.

Security
--------
WebREPL sends everything over clear-text (including the password 😓).
