# -*- coding: UTF-8 -*-
# Copyright, 2020, Leinad4Mind.
# This program is distributed under the terms of the GNU General Public License, version 2.
# http://www.gnu.org/licenses/gpl.txt


import os
from os.path import join as pjoin
import sys
import time
import unicodedata
import urllib
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
try:
    import simplejson as json
except:
    import json


_addon      = xbmcaddon.Addon()
_scriptname = _addon.getAddonInfo('name')
_language   = _addon.getLocalizedString
_dialog     = xbmcgui.Dialog()

debug   = _addon.getSetting('DEBUG')

SUB_EXTS          = ['srt', 'sub', 'txt', 'ass', 'ssa', 'smi']
HTTP_USER_AGENT   = 'User-Agent=Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.2.3) Gecko/20100401 Firefox/3.6.3 ( .NET CLR 3.5.30729)'

def _log(module, msg):
    s = u"### [%s] - %s" % (module, msg)
    xbmc.log(s.encode('utf-8'), level=xbmc.LOGDEBUG)


def log(msg=None):
    if debug == 'true': _log(_scriptname, msg)


def geturl(url):
    class MyOpener(urllib.FancyURLopener):
        #version = HTTP_USER_AGENT
        version = ''
    my_urlopener = MyOpener()
    log(u"Getting url: %s" % url)
    try:
        response = my_urlopener.open(url)
        content = response.read()
    except:
        log(u"Failed to get url:%s" % url)
        content = None
    return content


def enable_rar():

    def is_rar_enabled():
        q = '{"jsonrpc": "2.0", "method": "Addons.GetAddonDetails", "params": {"addonid": "vfs.rar", "properties": ["enabled"]}, "id": 0 }'
        r = json.loads(xbmc.executeJSONRPC(q))
        log(xbmc.executeJSONRPC(q))
        if r.has_key("result") and r["result"].has_key("addon"):
            return r['result']["addon"]["enabled"]
        return True

    if not is_rar_enabled():
        xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Addons.SetAddonEnabled", "params": {"addonid": "vfs.rar", "enabled": true} }')
        time.sleep(1)
        if not is_rar_enabled():
            ok = _dialog.ok(_language(32012).encode("utf-8"), _language(32013).encode("utf-8"), " ", _language(32014).encode("utf-8"))


def xbmc_walk(DIR):
    LIST = []
    dirs, files = xbmcvfs.listdir(DIR)
    for file in files:
        ext = os.path.splitext(file)[1][1:].lower()
        if ext in SUB_EXTS:
            LIST.append(os.path.join(DIR,  file))
    for dir in dirs:
        LIST.extend(list(xbmc_walk(os.path.join(DIR, dir))))
    return LIST


def extract_all_rar(archive_file, directory_to, archive_type):
    # zip and rar files will (currently) not copy contents with the 'archive://' vfs url.  They will copy if you use the 'zip://' or the 'rar://' url
    # 7z/bz2/gzip/xz/etc (all the formats that libarchive supports) will copy if you use the 'archive://' url
    # The contents of an rar/zip/7z etc will correctly be listed using xbmcvfs.listdir using 'archive://' regardless of the format.  
    # The builtin xbmc.extract does not work with 'archive://', only 'zip://' and 'rar://'
    log('---- Received Filed - Archive File: %s' % directory_to)
    log('---- Received Filed - Directory Folder: %s' % archive_file)
    log('---- Received Filed - Archive Type: %s' % archive_type)

    overall_success = True
    files_out = list()
    if archive_type != '':
        archive_path = (archive_type + '%s') % urllib.quote_plus(xbmc.translatePath(archive_file))
        archive_path_temp = ('archive://%s') % urllib.quote_plus(xbmc.translatePath(archive_file))
    else:
      archive_path = archive_file

    log('-----------------------------------------------------------')
    log('---- Extracting archive URL: %s' % archive_path)
    log('---- To directory: %s' % directory_to)
    
    log('---- Calling xbmcvfs.listdir...')
    try:
        (dirs_in_archive, files_in_archive) = xbmcvfs.listdir(archive_path)
    except:
        (dirs_in_archive, files_in_archive) = xbmcvfs.listdir(archive_path_temp)
    log('---- xbmcvfs.listdir CALLED...')

    for ff in files_in_archive:
        log('---- File found in archive: %s' % ff)
        url_from = os.path.join(archive_path, ff).replace('\\','/')  #Windows unexpectedly requires a forward slash in the path
        log('---- URL from: %s' % url_from)
        file_to = os.path.join(xbmc.translatePath(directory_to),ff)
        log('---- File to: %s' % file_to) 
        copy_success = xbmcvfs.copy(url_from, file_to) #Attempt to move the file first
        log('---- Calling xbmcvfs.copy...')

        if not copy_success:
            log('---- Copy ERROR!!!!!')
            overall_success = False
        else:
            log('---- Copy OK')
            files_out.append(file_to)

    for dd in dirs_in_archive:
        log('---- Directory found in archive: %s' % dd)
        
        dir_to_create = os.path.join(directory_to, dd)
        log('---- Directory to create: %s' % dir_to_create)
        
        log('---- Calling xbmcvfs.mkdir...')
        mkdir_success = xbmcvfs.mkdir(dir_to_create)

        if mkdir_success:

            log('---- Mkdir OK')
            
            dir_inside_archive_url = archive_path + '/' + dd + '/'
            log('---- Directory inside archive URL: %s' % dir_inside_archive_url)
            
            log('---- Calling extractArchiveToFolder...')
            files_out2, copy_success2 = extract_all_rar(dir_inside_archive_url, dir_to_create, '')
            
            if copy_success2:
                files_out = files_out + files_out2
            else:
                overall_success = False

        else:
            overall_success = False
            log('---- Mkdir ERROR!!!!!')

    return files_out, overall_success


def normalizeString(str):
    return unicodedata.normalize('NFKD', unicode(str, 'utf-8')).encode('ascii', 'ignore')


def get_params():
    param = []
    paramstring = sys.argv[2]
    if len(paramstring) >= 2:
        params = paramstring
        cleanedparams = params.replace('?', '')
        if params.endswith('/'):
            params = params[:-2]  # XXX: Should be [:-1] ?
        pairsofparams = cleanedparams.split('&')
        param = {}
        for pair in pairsofparams:
            splitparams = {}
            splitparams = pair.split('=')
            if len(splitparams) == 2:
                param[splitparams[0]] = splitparams[1]

    return param


def cleanDirectory(directory):
    try:
        if xbmcvfs.exists(directory + "/"):
            for root, dirs, files in os.walk(directory):
                for f in files:
                    file = os.path.join(root, f)
                    xbmcvfs.delete(file)
                for d in dirs:
                    dir = os.path.join(root, d)
                    xbmcvfs.rmdir(dir)
    except:
        pass
    if not xbmcvfs.exists(directory):
        xbmcvfs.mkdirs(directory)