# zap2xml - zap2it tvschedule scraper -

import time
from HTMLParser import HTMLParser
from htmlentitydefs import name2codepoint
import codecs

import platform
import sys
import os
import shutil
import logging
import traceback
import getopt
import calendar
import re
import gzip
import json
import cookielib
import urllib
import inspect
import urllib2
import datetime
"""
import requests
from requests.auth import HTTPBasicAuth
from BeautifulSoup import BeautifulSoup
import html2text
import Cookie
import zlib
import binascii
import urlparse
LWP::UserAgent #www.mechanize
XML::LibXML
libxml2
lxml

"""


class Zap2xmllog():
    debug = False
    quiet = False

    def __init__(self):
        logfile = os.path.join(os.path.dirname(os.path.realpath(__file__)),'zap2xml.log')
        if os.path.exists(logfile):
            os.unlink(logfile)
        logging.basicConfig(filename=logfile,level=logging.DEBUG,format='%(asctime)s %(message)s')

    def setDebug(self,x=True):
        self.debug = x

    def setQuiet(self,x=False):
        self.quiet = x


    def pout (self, pstr, log_type='none',printOut = True, func = False):
        if func:
            pstr += ':Function: ' + inspect.stack()[1][3] + ' :Line: ' + str(inspect.stack()[1][2])
        if printOut and not self.quiet:
            if log_type == 'debug':
                if self.debug:
                    print pstr
            else:
                print pstr
        if log_type == 'info':
            logging.info(pstr)
        if log_type == 'warn':
            logging.warning(pstr)
        if log_type == 'error':
            logging.error(pstr)
        if log_type == 'critical':
            logging.critical(pstr)
        if log_type == 'debug'and self.debug:
            logging.debug(pstr)
        if log_type == 'error' or log_type == 'critical':
            print log_type + repr(sys.exc_info()[0])
            logging.error(traceback.format_exc())


log = Zap2xmllog()
log.setDebug()
operSys = platform.uname()[0]
log.pout(repr(platform.uname()),'info',printOut = False)
kodiPath = '/storage/.kodi/addons/'
mechLib = 'script.module.mechanize/lib'
if re.search('openelec', platform.uname()[1], re.IGNORECASE) or os.path.exists(kodiPath):
    log.pout("Found openelec node name or " + kodiPath,'info',printOut = False)
    if os.path.exists(kodiPath + mechLib):
        sys.path.append(kodiPath + mechLib)
    else: log.pout("Mechanize addon not installed error",'error')
import mechanize

#log.pout("Test", 'debug', func=True)
# try:
#  homeDir = os.environ['HOME']
# except Exception as e:
#     homeDir = None
# try:
#  homeDir = os.environ['USERPROFILE']
# except Exception as e:
#  homeDir = None
# if homeDir is None : homeDir = homeDir='.'
# confFile = homeDir + '/.zap2xmlrc'

confFile = os.path.join(os.path.dirname(os.path.realpath(__file__)), ".zap2xmlrc")

# Defaults
start = 0
days = 7
ncdays = 0
ncsdays = 0
retries = 3
outFile = 'xmltv.xml'
cacheDir = 'cache'
lang = u'en'
userEmail = None
password = None

proxy = None
postalcode = None
lineupId = None

sleeptime = 0
shiftMinutes = 0

outputXTVD = None
includeXMLTV = None
lineuptype = None
lineupname = None
lineuplocation = None


sTBA = "\\bTBA\\b|To Be Announced"

urlRoot = 'http://tvschedule.zap2it.com/tvlistings/'
tvgurlRoot = 'http://mobilelistings.tvguide.com/'
tvgMapiRoot = 'http://mapi.tvguide.com/'
tvgurl = 'http://www.tvguide.com/'
br = None #browser global
gridHours = 0
loggedinMatchZ = 0
loggedinStr = '.*Logout of your Zap2it account.*'
programs = {}
cp = None
stations = {}
cs = None
rcs = None
schedule = {}
sch  = None
gridtimes = 0
mismatch = 0
coNum = 0
tb = 0
treq = 0
expired = 0
inStationTd = 0
inIcons = 0
inStationLogo = 0
iconDir = None
ua = None
tba = 0
exp = 0
count = None
zlineupId = None
zipcode = None
XTVD_startTime = None
XTVD_endTime = None
last_reSearchObj = None
tvgfavs = {}

# my favorite
def nop():
    return


def reSearch(regexp,string, flags):
    global last_reSearchObj
    last_reSearchObj = re.search(regexp,string,flags)
    return last_reSearchObj


# for image logo files
def getURLfile(url, fn):
    global retries, sleeptime
    rc = 0
    while rc < retries:
        log.pout("Getting: " + url,'info')
        try:
            mechanize.urlretrieve(url, fn)
            return
        except mechanize.HTTPError as e:
            log.pout(e.message,'error',func=True)
            time.sleep(sleeptime + 1)
            rc += 1
    log.pout('Failed to download within %d%s' % (retries, ' retries.\n'),'error', func=True)


def getURL(url):
    global br, tb, treq, retries, sleeptime

    if br is None:
        login()
    rc = 0
    while rc < retries:
        log.pout("Getting: " + url,'info')
        try:
            data = br.open(url).get_data()
            # data = br.open(url).read()
            data = unicode(data, 'utf-8')
            tb += len(data)
            treq += 1
            return data
        except mechanize.HTTPError as e:  # todo handle urlError
            log.pout(e.message,'error',func=True)
            time.sleep(sleeptime + 1)
            rc += 1
    log.pout('Failed to download within %d%s' % (retries, ' retries.\n'),'error', func=True)


def wbf(fn, data):
    with gzip.open(fn,"wb+") as f:
        d = data.encode('utf-8')  # turn into bytes/string so f.write doesn't try to make it ascii'
        f.write(d)
        f.close()


def copyLogo(key): # todo use os.join for this
    global iconDir,stations
    if iconDir is not None and "logo" in stations[key]:
        num = stations[key]["number"]
        src = iconDir + "/" + stations[key]["logo"] + stations[key]["logoExt"]
        dest1 = iconDir + "/" + num + stations[key]["logoExt"]
        dest2 = iconDir+ "/" + num  + stations[key]["name"] + stations[key]["logoExt"]
        #todo see if shutil is in openelec
        shutil.copy(src, dest1)
        shutil.copy(src, dest2)


def handleLogo(url):
    global stations, cs
    global iconDir
    try:
        os.stat(iconDir)
    except Exception as e:
        os.mkdir(iconDir)

    (dirName, fileName) = os.path.split(url)
    (fileBaseName, fileExtension)=os.path.splitext(fileName)
    stations[cs]["logo"] = fileBaseName
    stations[cs]["logoExt"] = fileExtension
    stations[cs]["logoURL"] = url
    f = iconDir + "/" + fileBaseName + fileExtension
    if not os.path.exists(f):
        getURLfile(url,f)
        #wbf(f, getURL(url))


def setOriginalAirDate():
    global cp,cs,sch
    if cp[10:13] != '0000':
        if "originalAirDate" not in programs[cp] or \
        int(schedule[cs][sch]["time"]) < int(programs[cp]["originalAirDate"]):
            programs[cp]["originalAirDate"] = schedule[cs][sch]["time"]


def on_th (self, tag, attrs):
    global inStationTd
    my_dict = {}
    cls = 'class'
    for attr in attrs:
        my_dict[attr[0]] = attr[1]
    if cls in my_dict:
        if re.search('zc-st',my_dict[cls]):
                 inStationTd = 1


def on_td (self, tag, attrs):
    global cs,rcs,sch,expired,exp,cp,inStationTd,schedule,programs,urlRoot

    my_dict = {}
    cls = 'class'
    onclk = 'onclick'
    for attr in attrs:
        my_dict[attr[0]] = attr[1]
    if cls in my_dict:
        if re.search('zc-pg',my_dict[cls]):
            if onclk in my_dict:
                cs = rcs #set in on_a
                oc = my_dict[onclk]
                tmp = re.search(".*\((.*)\).*",oc)
                oc = tmp.group(1)
                a = re.split(",",oc)
                cp = a[1]
                cp = re.sub("'",'',cp)
                sch = a[2]
                if len(cp) == 0 :
                    cp = cs = sch = -1
                    expired += 1
                    exp = 1
                if cs not in schedule:
                    schedule[cs] = {}
                if sch not in schedule[cs]:
                    schedule[cs][sch] = {}
                if cp not in programs:
                    programs[cp]= {}
                if "genres" not in programs[cp]:
                    programs[cp]["genres"] = {}

                schedule[cs][sch]["time"] = sch
                schedule[cs][sch]["program"] = cp
                schedule[cs][sch]["station"] = cs
                if re.search('zc-g-C',my_dict[cls]):
                    programs[cp]["genres"]["children"] = 1
                elif re.search('zc-g-N',my_dict[cls]):
                    programs[cp]["genres"]["news"] = 1
                elif re.search('zc-g-M',my_dict[cls]):
                    programs[cp]["genres"]["movie"] = 1
                elif re.search('zc-g-S',my_dict[cls]):
                    programs[cp]["genres"]["sports"] = 1

                if re.search("^MV",cp):
                    programs[cp]["genres"]["movie"] = 1
                elif re.search("^SP",cp):
                    programs[cp]["genres"]["sports"] = 1
                elif re.search("^EP",cp):
                    programs[cp]["genres"]["series"] = 9
                elif re.search("^SH",cp) and "-j" in options:
                    programs[cp]["genres"]["series"] = 9

                if cp != -1 and "-D" in options:
                    fn = os.path.join(cacheDir,cp + ".js.gz")
                    if not os.path.isfile(fn):
                        data = getURL(urlRoot + "gridDetailService?pgmId=" + cp)
                        wbf(fn, data)
                        log.pout("[D] Parsing: " + cp,'info')
                    parseJSOND(fn)
                if "-I" in options:
                    fn = os.path.join(cacheDir,"I" + cp + ".js.gz")
                    if not os.path.isfile(fn):
                        data = getURL(urlRoot + "gridDetailService?rtype=pgmimg&pgmId=" + cp)
                        if data: #sometimes we fail to get the url try to keep going
                            wbf(fn, data)
                            log.pout("[I] Parsing: " + cp,'info')
                    parseJSONI(fn)
        elif re.search('zc-st',my_dict[cls]):
            inStationTd = 1


def handleTags(text):
    global schedule,cs,sch
    if "rating" not in programs[cp]:
        if re.search("TV-Y",text):
            programs[cp]["rating"] = 'TV-Y'
        elif re.search("TV-Y7",text):
            programs[cp]["rating"] = 'TV-Y7'
        elif re.search("TV-G",text):
            programs[cp]["rating"] = 'TV-G'
        elif re.search("TV-PG",text):
            programs[cp]["rating"] = 'TV-PG'
        elif re.search("TV-14",text):
            programs[cp]["rating"] = 'TV-14'
        elif re.search("TV-MA",text):
            programs[cp]["rating"] = 'TV-MA'
    if re.search("LIVE",text):
        if "live" not in schedule[cs][sch]:
            schedule[cs][sch]["live"] = {}
        schedule[cs][sch]["live"] = 'Live'
        setOriginalAirDate()
    elif re.search("HD",text):
        if "quality" not in schedule[cs][sch]:
            schedule[cs][sch]["quality"] = {}
        schedule[cs][sch]["quality"] = 'HD'
    elif re.search("NEW",text):
        if "new" not in schedule[cs][sch]:
            schedule[cs][sch]["new"] = {}
        schedule[cs][sch]["new"] = 'New'
        setOriginalAirDate()


on_li_zc_ic = None


def on_li(self, tag, attrs):
    global schedule,cs,sch,on_li_zc_ic
    my_dict = {}
    cls = 'class'
    for attr in attrs:
        my_dict[attr[0]] = attr[1]
    if cls in my_dict:  #else nada
        if re.search('zc-ic-ne',my_dict[cls]):
            schedule[cs][sch]["new"] = 'New'
            setOriginalAirDate()
        elif re.search('zc-ic-cc',my_dict[cls]):
            schedule[cs][sch]["cc"] = 'CC'
        elif re.search('zc-ic',my_dict[cls]):
            on_li_zc_ic = True
        elif re.search('zc-icons-live',my_dict[cls]):
            schedule[cs][sch]["live"] = 'Live'
            setOriginalAirDate()
        elif re.search('zc-icons-hd',my_dict[cls]):
            schedule[cs][sch]["quality"] = 'HD'


def on_img(self, tag, attrs):
    global inIcons,schedule,cs,sch,inStationTd

    my_dict = {}
    for attr in attrs:
        my_dict[attr[0]] = attr[1]

    if inIcons:
        if re.search("Live",my_dict["alt"]):
            schedule[cs][sch]["live"] = "Live"
            setOriginalAirDate()
        elif re.search("New",my_dict["alt"]):
            schedule[cs][sch]["new"] = "New"
            setOriginalAirDate()
        elif re.search("HD",my_dict["alt"]) or re.search("High Definition",my_dict["alt"])\
        or re.search("video-hd",my_dict["src"]) or re.search("video-ahd",my_dict["src"]):
            schedule[cs][sch]["quality"] = "HD"
    elif inStationTd and re.search("Logo",my_dict["alt"]):
        if iconDir is not None:
            handleLogo(my_dict["src"])


def on_a(self, tag, attrs):
    global cbdata, inStationTd,cs,rcs,stations,coNum,postalcode,lineupId, count
    my_dict = {}
    cls = 'class'
    for attr in attrs:
        my_dict[attr[0]] = attr[1]
    if cls in my_dict:  #else nada
        if re.search('zc-pg-t',my_dict[cls]):
            #set global for text/data handling
            cbdata = 'title'
        elif inStationTd :
            tcs = my_dict['href']
            tmp = re.search(".*stnNum=(\w+).*",tcs)
            tcs = tmp.group(1)
            if not re.search("stnNum",tcs):
                cs = rcs = tcs
            if cs not in stations:
                stations[cs] = {}
            if "stnNum" not in stations[cs]:
                stations[cs]["stnNum"] = cs
            if "number" not in stations[cs]:
                tnum = urllib.unquote(my_dict["href"])
                tnum = re.sub("\s","",tnum)
                # match '.' or alphanumeric one or more time followed by anything
                tmp = re.search(".*channel=([.\w]+).*",tnum)
                if tmp:
                    tnum = tmp.group(1)
                else: tnum = "0"
                if not re.search("channel=",tnum):
                    stations[cs]["number"] = tnum
                if "order" not in stations[cs]:
                    if "-b" in options:
                        stations[cs]["order"] = coNum + 1
                    else:
                        stations[cs]["order"] = stations[cs]["number"]
            if postalcode is None and re.search("zipcode",my_dict["href"] ):
                postalcode = my_dict["href"]
                tmp = re.search(".*zipcode=(\w+).*",postalcode)
                postalcode = tmp.group(1)
            if lineupId is None and re.search("lineupId",my_dict["href"] ):
                lineupId = my_dict["href"]
                tmp = re.search(".*lineupId=(.*?)&.*",lineupId)
                lineupId = urllib.unquote(tmp.group(1))
            if count == 0 and inStationLogo and iconDir:
                fn = os.path.join(cacheDir,"STNNUM" + cs + ".html.gz")
                if not os.path.isfile(fn):
                    data = getURL(my_dict["href"])
                    #data = unicode(data,'utf8')
                    #data = data.encode('utf8')
                    wbf(fn,data)
                log.pout("[STNNUM] Parsing: " + cs,'info')
                parseSTNNUM(fn)


on_p_zc_pg_d = None


def on_p(self, tag, attrs):
    global on_p_zc_pg_d
    my_dict = {}
    for attr in attrs:
        my_dict[attr[0]] = attr[1]
    if "class" in my_dict and  re.search("zc-pg-d", my_dict["class"]):
        on_p_zc_pg_d = True

    return 0


on_div_zc_tn_c = None
on_div_zc_tn_t = None


def on_div(self, tag, attrs):
    global inIcons,inStationLogo,on_div_zc_tn_c, on_div_zc_tn_t
    my_dict = {}
    for attr in attrs:
        my_dict[attr[0]] = attr[1]

    if "class" in my_dict and  re.search("zc-icons", my_dict["class"]):
        inIcons= 1
    if "class" in my_dict and  re.search("zc-tn-c", my_dict["class"]):
        on_div_zc_tn_c = True
    if "class" in my_dict and  re.search("zc-tn-t", my_dict["class"]):
        on_div_zc_tn_t = True
    if "class" in my_dict and  re.search("stationLogo", my_dict["class"]):
        inStationLogo = 1

on_span_zc_pg_y = None
on_span_zc_pg_e = None
on_span_zc_st_c = None
on_span_zc_ic_s = None
on_span_zc_pg_t = None


def on_span(self, tag, attrs):
    global on_span_zc_pg_y, on_span_zc_pg_e, on_span_zc_st_c, on_span_zc_ic_s, on_span_zc_pg_t
    my_dict = {}
    for attr in attrs:
        my_dict[attr[0]] = attr[1]

    if "class" in my_dict:
        if re.search("zc-pg-y", my_dict["class"]):
            on_span_zc_pg_y = True
        elif re.search("zc-pg-e", my_dict["class"]):
            on_span_zc_pg_e = True
        elif re.search("zc-st-c", my_dict["class"]):
            on_span_zc_st_c = True
        elif re.search("zc-ic-s", my_dict["class"]):
            on_span_zc_ic_s = True
        elif re.search("zc-pg-t", my_dict["class"]):
            on_span_zc_pg_t = True


def loginZAP(br):
    global loggedinMatchZ, retries, sleeptime
    rc = 0
    while rc < retries :
       # The site we will navigate into, handling it's session
        log.pout( urlRoot + 'ZCLogin.do?method=getStandAlonePage&aid=tvschedule' + "\n",'info')
        br.open(urlRoot + 'ZCLogin.do?method=getStandAlonePage&aid=tvschedule')
        # View available forms
        for f in br.forms():
            log.pout("Form:\n" + str(f),'debug',printOut=False,func=True)

         # Select the second (index one) form (the first form is a search query box)
        br.select_form(name="zcLoginForm")
        br.form.find_control('username').readonly = False
        br.form.find_control('password').readonly = False
        # User credentials
        br.form['username'] = userEmail
        br.form['password'] = password

        # Login
        response = br.submit()
        # tmp1 = response.geturl()
        # tmp2 = response.info()

        # Invalid e-mail address/password. Please log in again.
        # look for Logout
        # todo find response success like perl script rather than search whole page
        matchString = response.read()
        m = loggedinMatchZ.search(matchString)
        if m:
            log.pout("Matched " + loggedinStr,'debug',func=True)
            return
        else:
            log.pout("Didn't Match %s %s %d %s" % (loggedinStr, 'Sleep ', sleeptime+1, "sec."),'debug',func=True)
            time.sleep(sleeptime + 1)
        rc += 1
    log.pout(("%s,%d,%s" % ("Failed to login within ", retries, " retries.\n")),'error',func=True)
    sys.exit(-1)


def login():
    global br, cj, proxy, options

    if userEmail is None or userEmail == '' or password is None or password == '':
        if zlineupId is None:
            log.pout("Unable to login: Unspecified username or password.\n",'error',func=True)
            exit(-1)

    # Browser
    br = mechanize.Browser()

    # Cookie Jar
    cj = cookielib.LWPCookieJar()
    br.set_cookiejar(cj)

    # Browser options
    if '-P' in options: # todo longer time out for proxies?
        br.set_proxies({'http':proxy})
    br.set_handle_equiv(True)
    br.set_handle_gzip(True)
    br.set_handle_redirect(True)
    br.set_handle_referer(True)
    br.set_handle_robots(False)
    br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)

    br.addheaders = [('User-agent', 'Mozilla/4.0')]

    if userEmail != '' and password != '':
        log.pout("Logging in as " + userEmail + "\n","info")
        if '-z' in options:
            loginTVG()
        else:
            loginZAP(br)
    else:
        log.pout("Connecting with lineupId \"" + zlineupId + "\" (" +  str(time.localtime(time.time())) +  ")\n",'info')



# s/\s+$// match white space at end of line one or more times and replace with nothing
# shift function args
def rtrim (shift):
  s = shift
  #s =~ s/\s+$//
  return re.sub("\s+$","",s)


def trim (shift):
  s = shift
  #$s =~ s/^\s+//
  #$s =~ s/\s+$//
  s = re.sub("^\s+","",s)
  s = re.sub("\s+$","",s)
  return s


# way to divide a string by 1000
def _rtrim3 (shift):
  s = shift
  return s[:-3]   #substr(s, 0, len(s)-3)


def convTime(t):
    global shiftMinutes
    t = int(t) + (shiftMinutes * 60 * 1000)
    return time.strftime("%Y%m%d%H%M%S",time.localtime(t/1000))


def convTimeXTVD(t):
    global shiftMinutes
    t = int(t) + (shiftMinutes * 60 * 1000)
    return time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime(t/1000))


def stationToChannel(s):
  if "-z" in options:
    return "I%s.%s.tvguide.com" % (stations[s]["number"], stations[s]["stnNum"])
  elif "-O" in options:
    return "C%s%s.zap2it.com" % (stations[s]["number"],stations[s]["name"].lower())
  return "I%s.labs.zap2it.com" % (stations[s]["stnNum"])

def convDateLocal(t):
    if int(t) < 0:
        tmp = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=(int(t)/1000))
        return tmp.strftime("%Y%m%d")
    return time.strftime("%Y%m%d", time.localtime((int(t)/1000)))

def convDateLocalXTVD(t):
    if int(t) < 0:
        tmp = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=(int(t)/1000))
        return tmp.strftime("%Y%m%d")
    return time.strftime("%Y-%m-%d", time.localtime((int(t)/1000)))


def convDurationXTVD(duration):
    dur = int(duration)
    hour = dur / 3600000
    minutes = (dur - (hour * 3600000)) / 60000
    return "PT%02dH%02dM" %(hour, minutes)


def appendAsterisk(title, station, s):
  if "-A" in options:
    if re.search("new",options["-A"]) and "new" in schedule[station][s]\
    or re.search("live",options["-A"]) and "live" in schedule[station][s]:
      title += " *"
  return title

cbdata = None


class MyHTMLParser(HTMLParser):
    entityref = None
    charref = None
    data_break = False
    handling_data = False

    def handle_starttag(self, tag, attrs):
        # print "Start tag:", tag
        # for attr in attrs:
        #     print "     attr:", attr
        if tag == 'td' or tag == 'a' or tag == 'th'\
        or tag == 'p' or tag == 'div'or tag == 'span'\
        or tag == 'li' or tag == 'img':
            globals()['on_%s' % tag](self, tag, attrs)

    def handle_endtag(self, tag):
        global inStationTd,inIcons, inStationLogo
        global cbdata,on_div_zc_tn_c,on_div_zc_tn_t
        global on_span_zc_pg_y, on_span_zc_pg_e, on_span_zc_st_c, on_span_zc_ic_s
        global on_span_zc_pg_t
        global on_p_zc_pg_d, on_li_zc_ic
       # print "End tag  :", tag
        if tag == 'td' or tag == 'th':
            inStationTd = 0
        if tag == 'a':
            cbdata = None
            self.handling_data = False
            self.data_break = False
        if tag == 'div':
            inIcons = 0
            inStationLogo = 0
            on_div_zc_tn_c = on_div_zc_tn_t = False
        if tag == 'span':
            on_span_zc_pg_y = on_span_zc_pg_e = on_span_zc_st_c = on_span_zc_ic_s = \
            on_span_zc_pg_t = self.handling_data = self.data_break = False
        if tag == 'p':
            on_p_zc_pg_d = False
        if tag == 'li':
            on_li_zc_ic = False
        if tag == 'head':
            head_found = False

    def handle_data(self, data):
        global programs,cbdata,cp,on_div_zc_tn_c,gridtimes,on_div_zc_tn_t
        global on_span_zc_pg_y, on_span_zc_pg_e, on_span_zc_st_c, on_span_zc_ic_s
        global on_span_zc_pg_t
        global tba, sTBA, stations, cs
        global on_p_zc_pg_d,on_li_zc_ic
        # print "Data     :", data

        if cbdata == 'title':       #set in on_a assume not special chars for now
            self.handling_data = True
            if cp not in programs:  #if so do tis like data and reset cbdata on 'a' end tag
                programs[cp] = {}
            if 'title' in programs[cp] and self.data_break:
                if self.entityref:
                    programs[cp]['title'] += self.entityref
                    self.entityref = None
                if self.charref:
                    programs[cp]["title"] += self.charref
                    self.charref = None
                programs[cp]['title'] += data
                self.data_break = False
            else:
                programs[cp]['title'] = data #find same program in mult files overwrite

        if  on_div_zc_tn_c is True:
            gridtimes = 0
            on_div_zc_tn_c = False
        if  on_div_zc_tn_t is True:
            gridtimes += 1
            on_div_zc_tn_t = False
        if on_span_zc_pg_y:
            data = re.sub("[^\d]","",data)
            programs[cp]["movie_year"] = data
            on_span_zc_pg_y = False
        if on_span_zc_pg_e:
            self.handling_data = True
            if "episode" in programs[cp] and self.data_break:   #entityref or charref event add and clr ref
                if self.entityref:
                    programs[cp]["episode"] += self.entityref
                    self.entityref = None
                if self.charref:
                    programs[cp]["episode"] += self.charref
                    self.charref = None
                programs[cp]["episode"] += data
                self.data_break = False
            else:
                programs[cp]["episode"] = data
            if re.search("$" + sTBA, data, re.IGNORECASE):
                tba = 1
            # on_span_zc_pg_e = False
        if on_span_zc_st_c:
            stations[cs]["name"] = trim(data)
            on_span_zc_st_c = False
        if on_span_zc_ic_s:
            handleTags(data)
            on_span_zc_ic_s = False
        if on_span_zc_pg_t:
            programs[cp]["title"] = data
            if re.search("$" + sTBA,data, re.IGNORECASE):
                tba = 1
            on_span_zc_pg_t = False
        if on_p_zc_pg_d:
            if 'description' not in programs[cp]: # needed to not overwrite -D option
                d = trim(data)
                if len(d):
                    programs[cp]["description"] = d
                on_p_zc_pg_d = False
        if on_li_zc_ic:
            handleTags(data)
            on_li_zc_ic = False

    # def handle_comment(self, data):
    #     print "Comment  :", data

    def handle_entityref(self, name): # &name like amp or apos
        if name in name2codepoint: #getting KeyError: 'B'
            # self.entityref = unichr(name2codepoint[name])
            tmp = name2codepoint[name]
            if tmp < 0x20 or tmp > 0x7f:    #not sure I need this, had encode error before codec.open encoding setting
                self.entityref = u"&#%d;" % tmp
            else:
                self.entityref = chr(tmp)
            if self.handling_data:
                self.data_break = True

    def handle_charref(self, name): # &# or &#x number
        if name.startswith('x'):
            #self.charref = chr(int(name[1:], 16))
            self.charref = unichr(int(name[1:], 16))
        else:
            #self.charref = chr(int(name))
            self.charref  = unichr(int(name))
        if self.handling_data:
            self.data_break = True

    #     print "Num ent  :", c
    # def handle_decl(self, data):
    #     print "Decl     :", data


def parseJSONI(fn):
    global programs, cp
    with gzip.open(fn,"rb") as f:
        b = f.read()
        f.close()
    b = re.sub("'","\"",b)
    t = json.loads(b)
    if "imageUrl" in t and re.search("^http",t["imageUrl"],re.IGNORECASE):
        programs[cp]["imageUrl"] = t["imageUrl"]


def parseJSOND(fn):
    global programs, cp
    with gzip.open(fn,"rb") as f:
        b = f.read()
        f.close()
    # todo figure out this re
    b = re.sub("^.+?\=","",b,re.IGNORECASE|re.MULTILINE)
    t = json.loads(b)
    p=t["program"]
    #todo remove xtra var like sn
    if "seasonNumber" in p:
        sn = p["seasonNumber"]
        sn = re.sub("S","",sn,re.IGNORECASE)
        if sn != '':
            programs[cp]["seasonNum"] = sn

    if "episodeNumber" in p:
        en = p["episodeNumber"]
        en = re.sub("E","",en,re.IGNORECASE)
        if en != '':
            programs[cp]["episodeNum"] = en

    if "originalAirDate" in p:
        oad = p["originalAirDate"]
        if oad != '':
            programs[cp]["originalAirDate"] = oad

    if "description" in p:
        desc = p["description"]
        if desc != '':
            programs[cp]["description"] = desc

    if "genres" in p:
        genres = p["genres"]
        i = 1
        for g in genres:
            programs[cp]["genres"][g.lower()] = i
            i += 1

    if "seriesId" in p:
        seriesId = p["seriesId"]
        if seriesId != '':
            programs[cp]["genres"]["series"] = 9

    if "credits" in p:
        credits = p["credits"]
        i = 1
        if"credits" not in programs[cp]:
            programs[cp]["credits"] = {}
        for g in credits:
            programs[cp]["credits"][g] = i
            i += 1

    if "starRating" in p:
        sr = p["starRating"]
        tsr = len(sr)
        if re.search("\+$",sr):
            tsr -= 1
            tsr += 0.5
        programs[cp]["starRating"] = str(tsr)



def parseTVGFavs(data):
    global tvgfavs, zlineupId
    t = json.loads(data)
    if 'message' in t:
        m = t['message']
        for f in m:
            source = f['source']
            channel = f['channel']
            tvgfavs[channel] = source
        log.pout("Lineup " + zlineupId + " favorites: " +  str(tvgfavs.keys()),'info')
    return

def sortPhash(a,b): # todo make ints and subtract?
    global sortThing1, sortThing2
    if b < a:
        return -1
    if b == a:
        return 0
    if b > a:
        return 1


def parseTVGD(fn):
    global programs, cp

    with gzip.open(fn,"rb") as f:
        b = f.read()
        f.close()

    t = json.loads(b)
    if 'program' in t:
        prog = t['program']
        if 'release_year' in prog:
            programs[cp]['movie_year'] = prog['release_year']
    if 'tvobject' in t:
        tvo = t['tvobject']
        if 'photos' in tvo:
            photos = tvo['photos']
            phash = {}
            for ph in photos:
                w = int(ph['width']) * int(ph['height'])
                u = ph['url']
                phash[w] = u
            big = sorted(phash.keys(),cmp=sortPhash)[0]
            programs[cp]['imageUrl'] = phash[big]
    return


def parseTVGGrid(fn):
    global programs, cp, cs, stations, coNum, tba, sTBA

    with gzip.open(fn,"rb") as f:
        b = f.read()
        f.close()
        t = json.loads(b)
    for e in t:
        cjs = e['Channel']
        cs = cjs['SourceId']
        if len(tvgfavs)> 0:
            if 'Number' in cjs and cjs['Number'] != '':
                n = cjs['Number']
            if n not in tvgfavs or cs != tvgfavs[n]:
                continue
        if cs not in stations:
            stations[cs] = {}
        if 'stnNum' not in stations[cs]:
            stations[cs]['stnNum'] = cs
            if 'Number' in cjs and  cjs['Number'] != '':
                stations[cs]['number'] = cjs['Number']
            stations[cs]['name'] = cjs['Name']
        if 'FullName' in cjs and cjs['FullName'] != cjs['Name']:
            stations[cs]['fullname'] = cjs['FullName']
        if 'order' not in stations[cs]:
            if '-b' in options:
                stations[cs]['order'] = coNum
                coNum += 1
            else:
                stations[cs]['order'] = stations[cs]['number']

        cps = e['ProgramSchedules']
        for pe in cps:
            cp = pe['ProgramId']
            catid = pe['CatId']
            if cp not in programs:
                programs[cp] = {}
            if 'genres' not in programs[cp]:
               programs[cp]['genres'] = {}
            if catid == 1:
                programs[cp]['genres']['movie'] = 1
            elif catid == 2:
                programs[cp]['genres']['sports'] = 1
            elif catid == 3:
                programs[cp]['genres']['family'] = 1
            elif catid == 4:
                programs[cp]['genres']['news'] = 1

            ppid = None
            if 'ParentProgramId' in pe:
               ppid = pe['ParentProgramId']
            if ppid and int(ppid) != 0:
                programs[cp]['genres']['series'] = 9

            programs[cp]['title'] = pe['Title']
            if re.search(sTBA, programs[cp]['title']):
                tba = 1
            if 'EpisodeTitle' in pe and pe['EpisodeTitle'] != '':
                programs[cp]['episode'] = pe['EpisodeTitle']
                if re.search(sTBA,  programs[cp]['episode']):
                    tba = 1
            if 'CopyText' in pe and pe['CopyText'] != '':
                programs[cp]['description'] = pe['CopyText']

            if 'Rating' in pe and pe['Rating'] != '':
                programs[cp]['rating'] = pe['Rating']

            sch = str(int(pe['StartTime']) *1000)
            if cs not in schedule:
                schedule[cs] = {}
            if sch not in schedule[cs]:
                schedule[cs][sch] = {}
            schedule[cs][sch]['time'] = sch
            schedule[cs][sch]['endtime'] = str(int(pe['EndTime']) * 1000)
            schedule[cs][sch]['program'] = cp
            schedule[cs][sch]['station'] = cs

            airat = pe['AiringAttrib']
            if airat & 1:
                schedule[cs][sch]['live'] = 1
            elif airat & 4:
                schedule[cs][sch]['new'] = 1
            # other bits?

            tvo = None
            if 'TVObject' in pe:
                tvo = pe['TVObject']
            if tvo:
                if 'SeasonNumber' in tvo and  tvo['SeasonNumber'] is not None:
                    programs[cp]['seasonNum'] = tvo['SeasonNumber']
                if 'EpisodeNumber' in tvo and  tvo['EpisodeNumber'] is not None:
                    programs[cp]['episodeNum'] = tvo['EpisodeNumber']

                if 'EpisodeAirDate' in tvo and tvo['EpisodeAirDate'] is not None:
                    eaid = tvo['EpisodeAirDate']
                #   $eaid =~ tr/0-9//cd;
                    eaid = re.sub('[^0-9]',"",eaid)
                    if eaid != '':
                        programs[cp]['originalAirDate'] = eaid
                if 'description' in tvo and tvo['description'] is not None:
                    programs[cp]['description'] = tvo['description']
                url = None
                if 'EpisodeSEOUrl' in tvo and tvo['EpisodeSEOUrl'] != '':
                    url = tvo['EpisodeSEOUrl']
                elif 'SEOUrl' in tvo and tvo['SEOUrl'] != '':
                    url = tvo['SEOUrl']
                    if catid == 1 and re.search('/movies', url):
                        url = '/movies' + url
                if url:
                    programs[cp]['url'] = tvgurl[:-1] + url

    if '-I' in options or ('-D' in options and catid ==1): # icons or details
        fn = os.path.join(cacheDir, str(cp) + ".js.gz")
        if not os.path.exists(fn):  #bug forgot not
            data = getURL(tvgMapiRoot + "listings/details?program=" + ("%d" % cp)) # Beware the headers
            wbf(fn,data)
        log.pout("[D] Parsing: " + str(cp), 'info')
        parseTVGD(fn)
    return


def parseGrid(fn):
    global html_charset, charset_found
    p = MyHTMLParser()
    with gzip.open(fn,"rb") as f:
        b = f.read()
    b = unicode(b,'utf-8') # now everything is in unicode see note in main()
    p.feed(b)
    f.close()
    p.close()


def on_stnum_img(self,tag,attrs):
    my_dict = {}
    for attr in attrs:
        my_dict[attr[0]] = attr[1]
    if 'id' in my_dict:
        if re.search('zc-ssl-logo', my_dict['id']):
            if iconDir is not None:
                handleLogo(my_dict['src'])


class MySTNUMParser(HTMLParser):
    def handle_starttag(self, tag, attrs):
        # print "STNUM Start tag:", tag
        # for attr in attrs:
        #     print "     attr:", attr
        if tag == 'img' :
            globals()['on_stnum_%s' % tag](self, tag, attrs)

    def handle_endtag(self, tag):
        return

    def handle_data(self, data):
        global programs,cbdata,cp,on_div_zc_tn_c,gridtimes,on_div_zc_tn_t
        # print "STNUM Data     :", data #todo

    # def handle_comment(self, data):
    #     print "Comment  :", data
    # def handle_entityref(self, name):
    #     c = unichr(name2codepoint[name])
    #     print "Named ent:", c
    # def handle_charref(self, name):
    #     if name.startswith('x'):
    #         c = unichr(int(name[1:], 16))
    #     else:
    #         c = unichr(int(name))
    #     print "Num ent  :", c
    # def handle_decl(self, data):
    #     print "Decl     :", data


def parseSTNNUM(fn):
    # my @report_tags = qw(img);
    p = MySTNUMParser()
    with gzip.open(fn,"rb") as f:
      b = f.read()
    p.feed(b)
    f.close()
    p.close()


def hourToMillis ():
    global start
    (year,mon,mday,hour,min,sec,wday,yday,isdst) = time.localtime(time.time())
    if start == 0 :
        hour = int(hour/gridHours) * gridHours
    else :
        hour = 0

    t = calendar.timegm((year,mon,mday,hour,0,0,wday,yday,isdst))
    if "-g" not in options: #todo no -g option in interface but this was in the code
        t = t - (tz_offset(0) * 3600)
    (year,mon,mday,hour,min,sec,wday,yday,isdst) = time.gmtime(t)

    t = calendar.timegm((year,mon,mday,hour,min,sec,wday,yday,isdst))
    return t*1000


def tz_offset(t) :

  if t == 0 :
    tt = time.time()
  else:
    tt = t
  (lyear,lmon,lmday,lhour,lmin,lsec,lwday,lyday,lisdst) = time.localtime(tt)
  (gyear,gmon,gmday,ghour,gmin,gsec,gwday,gyday,gisdst) = time.gmtime(tt)
  return (lmon - gmon)/60 + lhour - ghour + 24 * ((lyear - gyear) or (lyday - gyday))


def timezone(t) :

  if t == 0 :
    tztime = int(time.time())
  else :
    tztime = t/1000 #_rtrim3(t)
  #os = "%.1f" % ((calendar.timegm(time.localtime(tztime)) - tztime) / 3600)
  os = ((calendar.timegm(time.localtime(tztime)) - tztime) / 3600)
  mins = "%02d" % (abs( os - int(os) ) * 60)
  return "%+03d%s" % (int(os),mins)


#sub max ($$) { $_[$_[0] < $_[1]] } #todo
#sub min ($$) { $_[$_[0] > $_[1]] } #todo



def incXML (st, en, fh):
    xf = open(includeXMLTV)
    start_pat = False
    # How can I pull out lines between two patterns that are themselves on different lines?
    # You can use Perl's somewhat exotic .. operator (documented in perlop):
    # perl -ne 'print if /START/ .. /END/' file1 file2 ...
    # /^\s*$st/../^\s*$en/ st/ be st\  it seems to keep state
    regx1 = "^\s*" + st
    regx2 = "^\s*" + en
    for line in xf:
        if re.search(regx1,line) and start_pat == False : start_pat = True
        if start_pat and not re.search(regx2,line):
              fh.write(line)
        if re.search(regx2,line):
           start_pat = False
    xf.close()


# these cmp func need to be key objs too lazy right now
def sortChan(a,b):
    global stations

    if "order" in stations[a] and "order" in stations[b]:
        tmp = float(stations[a]["order"]) - float(stations[b]["order"])
        if tmp < 0.00:
            return -1
        if tmp == 0.00:
            return 0
        if tmp > 0.00:
            return 1
    else:
        if stations[a]["name"] < stations[b]["name"]:
            return -1
        if stations[a]["name"] == stations[b]["name"]:
            return 0
        if stations[a]["name"] > stations[b]["name"]:
            return 1


def hex2dec_e(matchObj):
    return "%s%d%s" % ('&#',ord(matchObj.group(1)),';')


# encodes back to the html entities
def enc(strng):
    global options
    t = strng
    if "-E" not in options:
        t = re.sub("&[^#]","&amp;",t)
        t = re.sub("\"","&quot;",t)
        t = re.sub("\'","&apos;",t)
        t = re.sub("<","&lt;",t)
        t = re.sub(">","&gt;",t)
    else:
        if re.search("amp",options["-E"]): t = re.sub("&[^#]","&amp;",t)
        if re.search("quot",options["-E"]): t = re.sub("\"","&quot;",t)
        if re.search("apos",options["-E"]): t = re.sub("\'","&apos;",t)
        if re.search("lt",options["-E"]): t = re.sub("<","&lt;",t)
        if re.search("gt",options["-E"]): t = re.sub(">","&gt;",t)
    # if "-e" in options:
    #     t = re.sub("([^\x20-\x7F])",hex2dec_e,t)  # handled by html parser make it unicode
    #     #$t =~ s/([^\x20-\x7F])/'&#' . ord($1) . ';'/gse;


    return t # unicodeData


def printHeader(fh , enc):
  fh.write("<?xml version=\"1.0\" encoding=\""+ enc + "\"?>\n")
  fh.write("<!DOCTYPE tv SYSTEM \"xmltv.dtd\">\n\n")
  if "-z" in options:
    fh.write("<tv source-info-url=\"http://tvguide.com/\" source-info-name=\"tvguide.com\"")
  else:
    fh.write("<tv source-info-url=\"http://tvschedule.zap2it.com/\" source-info-name=\"zap2it.com\"")
  fh.write(" generator-info-name=\"zap2xml\" generator-info-url=\"https://github.com/FastEddyCurrent/zap2xml\">\n")

def printFooter(fh):
  fh.write("</tv>\n")

def printChannels(fh):
    sname = None
    fname = None
    for key in sorted( stations, cmp=sortChan):
        if "name" in stations[key]:
            sname = enc(stations[key]["name"])
        if "fullname" in stations[key]:
            fname = enc(stations[key]["fullname"])
        snum = stations[key]["number"]
        fh.write("\t<channel id=\"" + stationToChannel(key) + "\">\n")
        if "-F" in options and sname is not None:
            fh.write("\t\t<display-name>" + sname + "</display-name>\n")
        if snum is not None:
            copyLogo(key)
            fh.write("\t\t<display-name>" + snum + " " + sname + "</display-name>\n")
            fh.write("\t\t<display-name>" + snum + "</display-name>\n")
        if "-F" not in options and sname is not None:
            fh.write("\t\t<display-name>" + sname + "</display-name>\n")
        if fname is not None:
            fh.write("\t\t<display-name>" + fname + "</display-name>\n")
        if "logoURL" in stations[key]:
            fh.write("\t\t<icon src=\"" + stations[key]["logoURL"] + "\" />\n")
        fh.write("\t</channel>\n")


def sortTime(a,b):
    global sortStation

    tmp = int(schedule[sortStation][a]["time"]) - int(schedule[sortStation][b]["time"])
    if tmp < 0:
        return -1
    if tmp == 0:
        return 0
    if tmp > 0:
        return 1


def sortThings(a,b): # todo make ints and subtract?
    global sortThing1, sortThing2
    if programs[sortThing1][sortThing2][a] < programs[sortThing1][sortThing2][b]:
        return -1
    if programs[sortThing1][sortThing2][a] == programs[sortThing1][sortThing2][b]:
        return 0
    if programs[sortThing1][sortThing2][a] > programs[sortThing1][sortThing2][b]:
        return 1


sortStation = None
sortThing1 = None
sortThing2 = None


def printProgrammes(fh):
    global stations,sortStation,sortThing1, sortThing2
    for station in sorted(stations, cmp=sortChan):
      i = 0
      sortStation = station
      keyArray = sorted(schedule[station], cmp=sortTime)
      for s in keyArray:
        if len(keyArray)-1 <= i and "endtime" not in schedule[station][s]:
            schedule[station][s].clear()
            continue
        p = schedule[station][s]["program"]
        startTime = convTime(schedule[station][s]["time"])
        startTZ= timezone(int(schedule[station][s]["time"]))
        if "endtime" in schedule[station][s]:
            endTime = schedule[station][s]["endtime"]
        else:
            endTime = schedule[station][keyArray[i+1]]["time"]
        # need obj that handles str ot int?
        stopTime = convTime(endTime)
        stopTZ = timezone(int(endTime))

        fh.write("\t<programme start=\"" + startTime + " " + startTZ + "\" stop=\"" + stopTime + " " + stopTZ + "\" channel=\""+ stationToChannel(schedule[station][s]["station"]) + "\">\n")
        if "title" in programs[p]:
            title = enc(programs[p]["title"])
            title = appendAsterisk(title, station, s)
            fh.write("\t\t<title lang=\"" + lang + "\">" + title + "</title>\n")
        if "episode" in programs[p] or ("-M" in options and "movie_year" in programs[p]):
            fh.write("\t\t<sub-title lang=\"" + lang + "\">")
            if "episode" in programs[p]:
                fh.write(enc(programs[p]["episode"]))
            else:
                fh.write("Movie (" + programs[p]["movie_year"] + ")")
            fh.write("</sub-title>\n")
        if "description" in programs[p] and programs[p]["description"] is not None:
            fh.write("\t\t<desc lang=\"" + lang + "\">")
            tmp = enc(programs[p]["description"]) + " "
            end = "</desc>\n"
            if "-X" in options:
                ratings = ""
                date=""
                new = ""
                live = ""
                hd = ""
                cc = ""
                bullet = u" \u2022 "
                if "originalAirDate" in programs[p]:
                    origdate = enc(convDateLocal(programs[p]["originalAirDate"]))
                    finaldate = datetime.datetime.strptime(origdate, "%Y%m%d").strftime('%B %d, %Y')
                    date = "Aired: " + finaldate
                if "movie_year" in programs[p]:
                    date = "Released: " + programs[p]["movie_year"]
                if "rating" in programs[p]:
                    ratings = enc(programs[p]["rating"]) + bullet
                if "new" in schedule[station][s]:
                    new = "NEW" + bullet
                    origdate = startTime
                    finaldate = datetime.datetime.strptime(origdate, "%Y%m%d%H%M%S").strftime('%B %d, %Y')
                    date = "Airs: " + finaldate
                if "live" in schedule[station][s]:
                    live = "LIVE" + bullet
                    origdate = startTime
                    finaldate = datetime.datetime.strptime(origdate, "%Y%m%d%H%M%S").strftime('%B %d, %Y')
                    date = "Airs: " + finaldate
                if "quality" in schedule[station][s]:
                    hd = "HD" + bullet
                if "cc" in schedule[station][s]:
                    cc = "CC" + bullet
                if "credits" in programs[p]:
                    global sortThing1, sortThing2
                    sortThing1= str(p)
                    sortThing2 = "credits"
                    cast = "Cast: "
                    castlist = ""
                    prev = None
                    for g in sorted(programs[p]["credits"], cmp=sortThings):
                        if prev is None:
                            castlist = enc(g)
                            prev = g
                        else:
                            castlist = castlist + ", " + enc(g)
                    cast = cast + castlist + bullet
                tmp = tmp + live + new + ratings + hd + cc + cast + date
            tmp = tmp + end
            fh.write(tmp)

        if "credits" in programs[p]:
            fh.write("\t\t<credits>\n")
            global sortThing1, sortThing2
            sortThing1= str(p)
            sortThing2 = "credits"
            for g in sorted(programs[p]["credits"], cmp=sortThings):
                fh.write("\t\t\t<actor>" + enc(g) + "</actor>\n")
            fh.write("\t\t</credits>\n")
        date = None
        if "movie_year" in programs[p]:
            date = programs[p]["movie_year"]
        # General note scrape, zap html get a str, use tvg  JSON get types so p can be an str or int
        # str(p) give str if str or int, int(p) gives int from int or str
        elif "originalAirDate" in programs[p] and re.search("^EP|^\d",str(p)):
            date = convDateLocal(programs[p]["originalAirDate"])
        if date is not None:
            fh.write("\t\t<date>" + str(date) + "</date>\n")
        sortThing1 = p
        sortThing2 = "genres"
        if "genres" in programs[p]:
            for g in sorted(programs[p]["genres"], cmp=sortThings):
                tmp = g[0].upper() + g[1:]
                fh.write("\t\t<category lang=\"" + lang + "\">" + enc(tmp) + "</category>\n")
        if "imageUrl" in programs[p]:
            fh.write("\t\t<icon src=\"" + programs[p]["imageUrl"] + "\" />\n")
        if "url" in programs[p]:
            fh.write("\t\t<url>" + programs[p]["url"] + "\" />\n")

        xs = None
        xe = None
        if "seasonNum" in programs[p] and "episodeNum" in programs[p]: # todo fixme another crop of JSON ints to deal with
            ss = programs[p]["seasonNum"]
            sf =  "S%0*d" % (max(2, len(str(ss))), int(ss))
            e = programs[p]["episodeNum"]
            ef = "E%0*d" % (max(2, len(str(e))), int(e))
            xs = int(ss) - 1
            xe = int(e) - 1
            if ss > 0 or e > 0:
                fh.write("\t\t<episode-num system=\"onscreen\">" + sf + ef + "</episode-num>\n")

        dd_prog_id = str(p)
        tmp = re.search("^(..\d{8})(\d{4})",dd_prog_id)
        if tmp:
            dd_prog_id = "%s.%s" % (tmp.group(1),tmp.group(2))
            fh.write("\t\t<episode-num system=\"dd_progid\">" + dd_prog_id  + "</episode-num>\n")
        if xs is not None and xe is not None and xs >= 0 and xe >= 0:
            fh.write("\t\t<episode-num system=\"xmltv_ns\">" + ("%d" % xs) +  "." + ("%d" % xe) + ".</episode-num>\n")
        if "quality" in  schedule[station][s]:
            fh.write("\t\t<video>\n")
            fh.write("\t\t\t<aspect>16:9</aspect>\n")
            fh.write("\t\t\t<quality>HDTV</quality>\n")
            fh.write("\t\t</video>\n")

        new = False
        live = False
        cc = False
        if "new" in schedule[station][s]:
            new = True
        if "live" in schedule[station][s]:
            live = True
        if "cc" in schedule[station][s]:
            cc = True
        if not new and not live and re.search("^EP|^SH|^\d", str(p)):
            fh.write("\t\t<previously-shown ")
            if "originalAirDate" in programs[p]:
                date = convDateLocal(programs[p]["originalAirDate"])
                fh.write("start=\"" + date + "000000\" ")
            fh.write("/>\n")
        if new:
            fh.write("\t\t<new />\n")
        # not part of XMLTV format yet?
        if live:
            fh.write("\t\t<live />\n")
        if cc:
            fh.write("\t\t<subtitles type=\"teletext\" />\n")
        if "rating" in programs[p]:
            fh.write("\t\t<rating>\n\t\t\t<value>" + programs[p]["rating"] + "</value>\n\t\t</rating>\n")
        if "starRating" in programs[p]:
            fh.write("\t\t<star-rating>\n\t\t\t<value>" + programs[p]["starRating"] + "/4</value>\n\t\t</star-rating>\n")
        fh.write("\t</programme>\n")
        i += 1


def printHeaderXTVD(fh, enc):
    global XTVD_startTime, XTVD_endTime
    fh.write("<?xml version=\'1.0\' encoding=\'enc\'?>\n")
    fh.write("<xtvd from=\'" + convTimeXTVD(XTVD_startTime) + "\' to=\'" + convTimeXTVD(XTVD_endTime)  + "\' schemaVersion=\'1.3\' xmlns=\'urn:TMSWebServices\' xmlns:xsi=\'http://www.w3.org/2001/XMLSchema-instance\' xsi:schemaLocation=\'urn:TMSWebServices http://docs.tms.tribune.com/tech/xml/schemas/tmsxtvd.xsd\'>\n")
    return


def printFooterXTVD(fh):
    fh.write("</xtvd>\n")
    return


def printLineupsXTVD(fh):
    global lineupId, lineupname, lineuplocation, lineuptype, postalcode
    if lineupId is None: lineupId = ''
    if lineupname is None: lineupname = ''
    if lineuplocation is None: lineuplocation = ''
    if lineuptype is None: lineuptype = ''
    if postalcode is None: postalcode = ''
    fh.write("<lineups>\n")
    fh.write("\t<lineup id=\'" + lineupId + "\' name=\'" + lineupname + "\' location=\'" + lineuplocation +
             "\' type=\'" + lineuptype + "\' postalCode=\'" + postalcode + "\'>\n")
    for key in sorted(stations,cmp=sortChan):
        if 'number' in stations[key]:
            fh.write("\t<map station='" + str(stations[key]['stnNum']) +
                     "\' channel=\'" + str(stations[key]['number']) + "\'></map>\n")
    fh.write("\t</lineup>\n")
    fh.write("</lineups>\n")
    return


def printStationsXTVD(fh):
    global stations
    fh.write("<stations>\n")
    for key in sorted(stations.keys(),cmp=sortChan):
        fh.write("\t<station id=\'" + str(stations[key]['stnNum']) + "\'>\n")
        if 'number' in stations[key]:
            sname = enc(stations[key]['name'])
            fh.write("\t\t<callSign>" + sname + "</callSign>\n")
            fh.write("\t\t<name>" + sname + "</name>\n")
            fh.write("\t\t<fccChannelNumber>" + stations[key]['number'] + "</fccChannelNumber>\n")
            if 'logo' in stations[key] and re.search("_affiliate", stations[key]['logo'],re.IGNORECASE):
                affiliate = stations[key]['logo']
                m = re.search('(.*)\_.*',affiliate)
                replace = m.group(1).upper()
                re.sub('(.*)\_.*',replace) #cna't (ha) seem to get /1 stuff to work id10t error
                fh.write("\t\t<affiliate>" + affiliate + " Affiliate</affiliate>\n")
            copyLogo(key)
        fh.write("\t</station>\n")
    fh.write("\t</stations>\n")
    return

def printSchedulesXTVD(fh):
    global stations,sortStation

    fh.write("<schedules>\n")
    for station in sorted( stations, cmp=sortChan):
      i = 0
      sortStation = station
      keyArray = sorted(schedule[station], cmp=sortTime)
      for s in keyArray:
        if len(keyArray)-1 <= i:
            schedule[station][s].clear()
            continue
        p = schedule[station][s]['program']
        startTime = convTimeXTVD(schedule[station][s]['time'])
        stopTime = convTimeXTVD(schedule[station][keyArray[i+1]]['time'])
        duration = convDurationXTVD(int(schedule[station][keyArray[i+1]]['time']) - int(schedule[station][s]['time']))

        fh.write("\t<schedule program=\'" + str(p) + "\' station=\'" + str(stations[station]['stnNum']) +
        "' time=\'" + startTime + "\' duration=\'" + duration + "\'")
        if 'quality' in schedule[station][s]:
            fh.write(" hdtv='true' ")
        if 'new' in schedule[station][s] or  'live' in schedule[station][s]:
            fh.write(" new='true' ")
        fh.write("/>\n")
        i += 1

    return


def printProgramsXTVD(fh):
    global programs
    fh.write("<programs>\n")
    for p in programs.keys():
        fh.write("\t<program id=\'" + str(p) + "\'>\n")
        if 'title' in programs[p]:
            fh.write("\t\t<title>" + enc(programs[p]['title']) + "</title>\n")
        if 'episode' in programs[p]:
            fh.write("\t\t<subtitle>" + enc(programs[p]['episode']) + "</subtitle>\n")
        if 'description' in programs[p]:
            fh.write("\t\t<description>" + enc(programs[p]['description']) + "</description>\n")

        if 'movie_year' in programs[p]:
            fh.write("\t\t<year>" + programs[p]['movie_year'] + "</year>\n")
        else: # Guess
            showType = "Series"
            if re.search('Paid Programming', programs[p]['title'],re.IGNORECASE):
                showType = "Paid Programming"
            fh.write("\t\t<showType>$showType</showType>\n")
            fh.write("\t\t<series>EP" + str(p)[2:8] + "</series>\n")
            if 'originalAirDate'in programs[p]:
                fh.write("\t\t<originalAirDate>" + convDateLocalXTVD(programs[p]['originalAirDate']) +
                         "</originalAirDate>\n")
        fh.write("\t</program>\n")
    fh.write("\t</programs>\n")
    return


def printGenresXTVD(fh):
    global programs
    fh.write("<genres>\n")
    for p in programs.keys():
       if 'genres' in programs[p] and 'movies' not in programs[p]['genres']:   # todo need int()?
        fh.write("\t<programGenre program=\'" + str(p) + "\'>\n")
        for g in programs[p]['genres'].keys():
            fh.write("\t\t<genre>\n")
            fh.write("\t\t\t<class>" + enc(str(g).capitalize()) + "</class>\n")
            fh.write("\t\t\t<relevance>0</relevance>\n")
            fh.write("\t\t</genre>\n")
        fh.write("\t</programGenre>\n")
    fh.write("</genres>\n")
    return


def loginTVG():
    global cj, zlineupId, br

    # data = getURL(tvgurl + 'user/_modal/')
    data = getURL(tvgurl + 'signin/')
    m = re.search('<input.+name=\"_token\".+?value=\"(.*?)\"',data,re.IGNORECASE)
    # View available forms
    for f in br.forms():
        log.pout("Form:\n" + str(f),'debug',printOut=False,func=True)
    if m:
        token = m.group(1)
        br.form = list(br.forms())[2]
        br.form.find_control('email').readonly = False
        br.form.find_control('password').readonly = False
        br.form.find_control('_token').readonly = False
        # User credentials
        br.form['email'] = userEmail
        br.form['password'] = password
        br.form['_token'] = token

        # Login
        response = br.submit()
        tmp1 = response.geturl()
        tmp2 = response.info()

        for cookie in cj:
            log.pout('Cookie:\n' + str(cookie),'info',func=True)
            if re.search('ServiceID',cookie.name):
                zlineupId = cookie.value
                break
        if '-a' not in options:
            url = tvgurl + 'user/favorites/?provider=' + zlineupId
            br.addheaders.append(('X-Requested-With', 'XMLHttpRequest')) # to get json data
            data = getURL(url)
            tmp1 = br.addheaders.pop()  # remove added header
            parseTVGFavs(data)

    else:
        log.pout("Failed to login within %d%s" %(retries, " retries."))
    return


def deleteOldCache():

    if os.path.exists(cacheDir):
        entries = os.listdir(cacheDir)
        for entry in entries:
            if re.search("\.html|\.js", entry):
                fn = os.path.join(cacheDir,entry)
                atime = os.stat(fn)[8]
                if (atime + ((days + 2) *86400) < time.time()):
                    log.pout("Deleting old cached file: " + fn +"\n", 'info')
                    os.unlink(fn)

options = {}
def option_parse():

    global options
    global confFile, start, days, ncdays, ncsdays, retries, outFile, cacheDir, iconDir, trailerDir
    global lang, userEmail, password, proxy, postalcode, lineupId, sleeptime, shiftMinutes
    global outputXTVD, includeXMLTV, lineuptype, lineupname, lineuplocation, zlineupId, zipcode

    optlist = args = None
    optlist, args  = getopt.getopt(sys.argv[1:], "?aA:bc:C:d:DeE:Fgi:Il:jJ:Lm:Mn:N:o:Op:P:qr:s:S:t:Tu:UwxY:zZ:X")
    options = dict(optlist)
    if "-?" in options:
        printHelp()

    if "-q" in options: log.setQuiet(True)
    if os.path.exists(confFile):
        log.pout ("Reading config file: " + confFile + "\n",'info')
        cf = open(confFile)
        conf = None
        for conf in cf: #todo this code needs array or dict of options
            re.sub("#.*","",conf) #blow away comment
            if reSearch("^\s*$",conf,re.IGNORECASE): #ignore white space
                nop()
            elif reSearch("^\s*start\s*=\s*(\d+)", conf,re.IGNORECASE):
                start = last_reSearchObj.group(1)
            elif reSearch("^\s*days\s*=\s*(\d+)", conf,re.IGNORECASE):
                days = last_reSearchObj.group(1)
            elif reSearch("^\s*ncdays\s*=\s*(\d+)", conf,re.IGNORECASE):
                ncdays = last_reSearchObj.group(1)
            elif reSearch("^\s*ncsdays\s*=\s*(\d+)", conf,re.IGNORECASE):
                ncsdays = last_reSearchObj.group(1)
            elif reSearch("^\s*retries\s*=\s*(\d+)", conf,re.IGNORECASE):
                retries = last_reSearchObj.group(1)
            elif reSearch("^\s*user[\w\s]*=\s*(.+)", conf,re.IGNORECASE):
                userEmail = rtrim(last_reSearchObj.group(1))
            elif reSearch("^\s*pass[\w\s]*=\s*(.+)", conf,re.IGNORECASE):
                password = rtrim(last_reSearchObj.group(1))
            elif reSearch("^\s*cache\s*=\s*(.+)", conf,re.IGNORECASE):
                cacheDir = rtrim(last_reSearchObj.group(1))
            elif reSearch("^\s*icon\s*=\s*(.+)", conf,re.IGNORECASE):
                iconDir = rtrim(last_reSearchObj.group(1))
            elif reSearch("^\s*trailer\s*=\s*(.+)", conf,re.IGNORECASE):
                trailerDir = rtrim(last_reSearchObj.group(1))
            elif reSearch("^\s*lang\s*=\s*(.+)", conf,re.IGNORECASE):
                lang = rtrim(last_reSearchObj.group(1))
            elif reSearch("^\s*outfile\s*=\s*(.+)", conf,re.IGNORECASE):
                outFile = rtrim(last_reSearchObj.group(1))
            elif reSearch("^\s*proxy\s*=\s*(.+)", conf,re.IGNORECASE):
                proxy = rtrim(last_reSearchObj.group(1))
            elif reSearch("^\s*outformat\s*=\s*(.+)", conf,re.IGNORECASE):
                outputXTVD = rtrim(last_reSearchObj.group(1))
            elif reSearch("^\s*lineupid\s*=\s*(.+)", conf,re.IGNORECASE):
                lineupId = rtrim(last_reSearchObj.group(1))
            elif reSearch("^\s*lineupname\s*=\s*(.+)", conf,re.IGNORECASE):
                lineupname = rtrim(last_reSearchObj.group(1))
            elif reSearch("^\s*lineuptype\s*=\s*(.+)", conf,re.IGNORECASE):
                lineuptype = rtrim(last_reSearchObj.group(1))
            elif reSearch("^\s*lineuplocation\s*=\s*(.+)", conf,re.IGNORECASE):
                lineuplocation = rtrim(last_reSearchObj.group(1))
            elif reSearch("^\s*postalcode\s*=\s*(.+)", conf,re.IGNORECASE):
                postalcode = rtrim(last_reSearchObj.group(1))


    if optlist is None and userEmail is None:
        printHelp()

    if "-c" in options: cacheDir = options["-c"]
    if "-d" in options: days = int(options["-d"])
    if "-n" in options: ncdays = int(options["-n"])
    if "-N" in options: ncsdays = int(options["-N"])
    if "-s" in options: start = int(options["-s"])
    if "-r" in options: retries = int(options["-r"])
    if "-i" in options: iconDir = options["-i"]
    if "-t" in options: trailerDir = options["-t"]
    if "-l" in options: lang = options["-l"]
    if "-x" in options:
        outFile = 'xtvd.xml'
        outputXTVD = 1
    if "-o" in options: outFile = options["-o"]
    if "-p" in options: password = options["-p"]
    if "-u" in options: userEmail = options["-u"]
    if "-P" in options: proxy = options["-P"]
    if "-Y" in options: zlineupId = options["-Y"]
    if "-Z" in options: zipcode = options["-Z"]
    if "-J" in options and os.path.exists(options["-J"]): includeXMLTV = options["-J"]
    if "-S" in options: sleeptime = float(options["-S"])
    if "-m" in options: shiftMinutes = int(options["-m"])



def printHelp ():
    global sTBA, start, outFile, cacheDir, lang, retries, confFile
    print ("\
zap2xml <zap2xml_python\@something.com> (2015-12-14)\n\
-u <username>\
-p <password>\n\
-d <# of days> (default = " + ("%d" % days) + ")\n\
-n <# of no-cache days> (from end)   (default = "+ ("%d" % ncdays) + ")\n\
-N <# of no-cache days> (from start) (default = " + ("%d" % ncsdays) + ")\n\
-s <start day offset> (default = "+ ("%d" % start) +")\n\
-o <output xml filename> (default = "+ outFile + ")\n\
-c <cacheDirectory> (default = "+ cacheDir +")\n\
-l <lang> (default =" + lang + ")\n\
-i <iconDirectory> (default = don't download channel icons, not supported for TVGUIDE)\n\
-m <#> = offset program times by # minutes (better to use TZ env var)\n\
-b = retain website channel order\n\
-x = output XTVD xml file format (default = XMLTV)\n\
-w = wait on exit (require keypress before exiting)\n\
-q = quiet (no status output)\n\
-r <# of connection retries before failure> (default = "+ ("%d" % retries) +", max 20)\n\
-E \"amp apos quot lt gt\" = selectively encode standard XML entities\n\
-F = output channel names first (rather than \"number name\")\n\
-O = use old tv_grab_na style channel ids (C###nnnn.zap2it.com)\n\
-A \"new live\" = append \" *\" to program titles that are \"new\" and/or \"live\"\n\
-M = copy movie_year to empty movie sub-title tags\n\
-L = ((option removed)) output \"<live />\" tag (not part of xmltv.dtd)\n\
-T = don't cache files containing programs with \""+sTBA +"\" titles \n\
-P <http://proxyhost:port> = to use an http proxy\n\
-C <configuration file> (default = \"" + confFile +"\")\n\
-S <#seconds> = sleep between requests to prevent flooding of server\n\
-D = include details = 1 extra http request per program!\n\
-I = include icons (image URLs) - 1 extra http request per program!\n\
-X = append extra details to program description\n\
-J <xmltv> = include xmltv file in output\n\
-Y <lineupId> (if not using username/password)\n\
-Z <zipcode> (if not using username/password)\n\
-z = use tvguide.com instead of zap2it.com\n\
-a = output all channels (not just favorites) on tvguide.com\n\
-j = add \"series\" category to all non-movie programs")
    if operSys == "Windows":  #why??
        time.sleep(5)
    exit (0)

"""
-u <username>\                                                                      DONE
-p <password>\n\                                                                    DONE
-d <# of days> (default = " + ("%d" % days) + ")\n\                                 DONE
-n <# of no-cache days> (from end)   (default = "+ ("%d" % ncdays) + ")\n\          DONE
-N <# of no-cache days> (from start) (default = " + ("%d" % ncsdays) + ")\n\        DONE
-s <start day offset> (default = "+ ("%d" % start) +")\n\                           DONE
-o <output xml filename> (default = "+ outFile + ")\n\                              DONE
-c <cacheDirectory> (default = "+ cacheDir +")\n\                                   DONE
-l <lang> (default =" + lang + ")\n\                                                DONE
-i <iconDirectory> (default = don't download channel icons)\n\                      DONE
-m <#> = offset program times by # minutes (better to use TZ env var)\n\            DONE
-b = retain website channel order\n\                                                DONE
-x = output XTVD xml file format (default = XMLTV)\n\                               DONE
-w = wait on exit (require keypress before exiting)\n\                              DONE
-q = quiet (no status output)\n\                                                            DONE
-r <# of connection retries before failure> (default = "+ ("%d" % retries) +", max 20)\n\   DONE
-e = hex encode entities (html special characters like accents)\n\                          Remove as option handled in html parser
-E \"amp apos quot lt gt\" = selectively encode standard XML entities\n\                    DONE
-F = output channel names first (rather than \"number name\")\n\                            DONE
-O = use old tv_grab_na style channel ids (C###nnnn.zap2it.com)\n\                          DONE
-A \"new live\" = append \" *\" to program titles that are \"new\" and/or \"live\"\n\       DONE
-M = copy movie_year to empty movie sub-title tags\n\                                       DONE
-U = UTF-8 encode output xml file (default = \"ISO-8859-1\")\n\                             REMOVE use UTF-8 only
-L = ((option removed)) output \"<live />\" tag (not part of xmltv.dtd)\n\                  Removed as option
-T = don't cache files containing programs with \""+sTBA +"\" titles \n\                    DONE
-P <http://proxyhost:port> = to use an http proxy\n\                                        DONE
-C <configuration file> (default = \"" + confFile +"\")\n\                                  DONE
-S <#seconds> = sleep between requests to prevent flooding of server\n\                     DONE
-D = include details = 1 extra http request per program!\n\                                 DONE
-I = include icons (image URLs) - 1 extra http request per program!\n\                      DONE
-X = append extra details to program description\n\                                         DONE
-J <xmltv> = include xmltv file in output\n\                                                DONE
-Y <lineupId> (if not using username/password)\n\                                           TEST FIX
-Z <zipcode> (if not using username/password)\n\                                            TEST FIX dump lineup for zipcode
-z = use tvguide.com instead of zap2it.com\n\                                               DONE
-a = output all channels (not just favorites) on tvguide.com\n\                             IMPLEMENT
-j = add \"series\" category to all non-movie programs")                                    DONE
"""


def main():
    global loggedinMatchZ, count, XTVD_startTime, XTVD_endTime, zlineupId, outFile
    global gridHours, ncsdays, ncdays, days, cacheDir, gridtimes,exp,tba, mismatch,includeXMLTV
    try:
        option_parse()
        s1 = time.time()
        cacheDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), cacheDir)
        if not os.path.exists(cacheDir):
            os.mkdir(cacheDir)
        deleteOldCache()

        if '-z' in options:
            if '-i' in options:
                log.pout("Warning -i option not supported for TV Guide\n",'warn')
            if '-a' not in options:  #oops missed not
                login()
            gridHours = 3
            maxCount = days * (24 / gridHours)
            ncCount = maxCount - (ncdays * (24 / gridHours))
            offset = start * 3600 * 24 * 1000
            ncsCount = ncsdays * (24 / gridHours)
            ms = hourToMillis() + offset
            count = 0
            while count < maxCount:
                if count == 0:
                    XTVD_startTime = ms
                elif count == maxCount - 1:
                    XTVD_endTime = ms + (gridHours * 3600000) - 1
                fn = os.path.join(cacheDir, "%s"%(ms) + ".js.gz")
                if not os.path.exists(fn) or count >= ncCount or count < ncsCount:
                    if zlineupId is None:
                        login()
                    duration = gridHours * 60
                    tvgstart = ms/1000
                    data = getURL(tvgurlRoot + "Listingsweb/ws/rest/schedules/%s%s%d%s%d"
                                               % (zlineupId, "/start/", tvgstart, "/duration/", duration))
                    wbf(fn,data)
                log.pout("[%d%s%d%s" % (count+1,"/",maxCount,"] Parsing:" + fn))
                parseTVGGrid(fn)
                if "-T" in options and tba:
                    log.pout("Deleting: " + fn + " (contains \"" + sTBA + "\")\n",'warn')
                    os.unlink(fn)
                if exp:
                    log.pout("Deleting: " + fn + " (expired)\n",'warn')
                    os.unlink(fn)
                exp = 0
                tba = 0
                ms += gridHours * 3600 * 1000
                count += 1
        else:
            # loggedinMatchZ = re.compile('.*Welcome.*Logout.*')
            # todo find response success like perl script
            loggedinMatchZ = re.compile(loggedinStr)
            gridHours = 6
            maxCount = days * (24 / gridHours)
            ncCount = maxCount - (ncdays * (24 / gridHours))
            offset = start * 3600 * 24 * 1000
            ncsCount = ncsdays * (24 / gridHours)
            ms = hourToMillis() + offset
            # print "ms %d \n" %(ms)
            count = 0
            while count < maxCount:
                if count == 0:
                    XTVD_startTime = ms
                elif count == maxCount - 1:
                    XTVD_endTime = ms + (gridHours * 3600000) - 1
                fn = os.path.join(cacheDir, "%s"%(ms) + ".html.gz")
                if not os.path.exists(fn) or count >= ncCount or count < ncsCount:
                    params = ""
                    if zlineupId is not None:
                        params += "&lineupId=" + zlineupId
                    if zipcode is not None:
                        params += "&zipcode=" + zipcode
                    url = "%s%d%s%s" %(urlRoot + "ZCGrid.do?isDescriptionOn=true&fromTimeInMillis=",ms,params,"&aid=tvschedule")
                    # Note about the string/unicode Python 2.7 issue
                    # Found data from mechanize browser is a string with out of range bytes
                    # that can't be  converted tounicode
                    # After zip writing the html and reading it I can unicode it without error (magic)
                    # Avoid the unicode ascii error on the xml file write by using codec.open, codec.write
                    data = getURL(url)
                    wbf(fn,data)

                parseGrid(fn) #data read in and unicode it
                log.pout(("%s%d%s%d%s%s" % ("[",(count+1),"/", maxCount, "] Parsing: ", fn)) , 'info')
                if count == 0:
                    gridHours = gridtimes / 2
                    if gridHours < 1:
                        log.pout("Error: The grid is not being displayed, try logging in to the zap2it website\n", 'error')
                        log.pout(("Deleting: " + fn + "\n"), 'warn',func=True)
                        os.unlink(fn)
                        exit(1)
                    elif gridHours != 6:
                        log.pout(("%s%d%s" % ("Notice: \"Six hour grid\" not selected in zap2it preferences, adjusting to ", gridHours, " hour grid\n")),'warn')
                    maxCount = days * (24 / gridHours)
                    ncCount = maxCount - (ncdays * (24 / gridHours))
                    ncsCount = ncsdays * (24 / gridHours)
                elif mismatch == 0 :
                    if gridHours != gridtimes / 2:
                        log.pout("Notice: Grid mismatch in cache, ignoring cache & restarting.\n",'warn')
                        mismatch = 1
                        ncsdays = 99
                        ncsCount = ncsdays * 24
                        ms = hourToMillis() + offset
                        count = -1
                        gridtimes = 0
                        continue # skip ms incr
                gridtimes = 0
                if "-T" in options and tba:
                    log.pout("Deleting: " + fn + " (contains \"" + sTBA + "\")\n",'warn')
                    os.unlink(fn)
                if exp:
                    log.pout("Deleting: " + fn + " (expired)\n",'warn')
                    os.unlink(fn)
                exp = 0
                tba = 0
                ms += gridHours * 3600 * 1000
                count += 1

        s2 = time.time()
        log.pout(("Downloaded %d%s%d%s" %(tb," bytes in ",treq," http requests.\n")),'info')
        if expired > 0:
            log.pout("Expired programs: " + ("%d" % expired) + "\n",'info')
        outFile = os.path.join(os.path.dirname(os.path.realpath(__file__)),outFile)
        log.pout("Writing XML file: " + outFile + "\n",'info')
        # enc = 'ISO-8859-1'  # f this it's only 256 chars
        # codec = 'iso8859-1'
        # if "-U" in options: # therefore this option should be the only one i.e. no option
        enc = 'UTF-8'
        # codec = 'utf8'
        fh = codecs.open(outFile, 'w+b', encoding=enc)
        if outputXTVD is not None:
            printHeaderXTVD(fh, enc)
            printStationsXTVD(fh)
            printLineupsXTVD(fh)
            printSchedulesXTVD(fh)
            printProgramsXTVD(fh)
            printGenresXTVD(fh)
            printFooterXTVD(fh)
        else:
            printHeader(fh, enc)
            printChannels(fh)
            if includeXMLTV is not None:
                log.pout("Reading XML file: " + includeXMLTV + "\n",'info')
                incXML("<channel","<programme", fh)
            printProgrammes(fh)
            if includeXMLTV is not None:
                incXML("<programme","</tv", fh)
        printFooter(fh)

        fh.close()

        ts = 0
        for station in stations:
            ts += len(schedule[station])

        s3 = time.time()
        log.pout("Completed in %d%s%d%s%d%s%d%s%d%s" % (( s3 - s1 ),"s (Parse: ", ( s2 - s1 ), "s) ",
            len(stations)," stations, ", len(programs), " programs, ", ts, " scheduled.\n"),'info')
        global operSys
        if "-w" in options:
            log.pout("Press ENTER to exit:",'none')
            raw_input()
        elif operSys == "Windows": # port don't know why
            time.sleep(3)

    except Exception as e:
        log.pout('Exception', 'error')
        raise
    exit(0)


if __name__ == "__main__":
    main()
