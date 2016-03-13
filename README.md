# zap2xml
zap2xml in Python 2.7 for use on the RaspberryPI

Requires Mechanize addon from superrepo

https://superrepo.org/kodi/addon/script.module.mechanize/

View this in raw mode

crontab entry

*     *     *   *    *        command to be executed
-     -     -   -    -
|     |     |   |    |
|     |     |   |    +----- day of week (0 - 6) (Sunday=0)
|     |     |   +------- month (1 - 12)
|     |     +--------- day of        month (1 - 31)
|     +----------- hour (0 - 23)
+------------- min (0 - 59)
crontab -e example

0 2 * * 0,3 /usr/bin/python /storage/downloads/zap2xml/zap2xml.py

Every 2 am on Sunday and Wednesday
