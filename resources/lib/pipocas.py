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
import archive_tool
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
    log('---- Received Filed - Archive File: %s' % archive_file)
    log('---- Received Filed - Directory Folder: %s' % directory_to)
    log('---- Received Filed - Archive Type: %s' % archive_type)

    overall_success = True
    files_out = list()
    if archive_type != '':
        archive_path = (archive_type + '%s') % urllib.quote_plus(xbmc.translatePath(archive_file))
        # archive_path_temp = ('archive://%s') % urllib.quote_plus(xbmc.translatePath(archive_file))
    else:
      archive_path = archive_file

    log('-----------------------------------------------------------')
    log('---- Extracting archive URL: %s' % archive_path)
    log('---- To directory: %s' % directory_to)
    
    log('---- Calling xbmcvfs.listdir...')
    # try:
    #     (dirs_in_archive, files_in_archive) = xbmcvfs.listdir(archive_path)
    # except:
    #     (dirs_in_archive, files_in_archive) = xbmcvfs.listdir(archive_path_temp)
    # log('---- xbmcvfs.listdir CALLED...')
    if archive_type == 'rar://':
        dirs_in_archive = archive_tool.archive_tool(archive_file, directory_to, use_vfs_rar=True) #current archive object using vfs.rar instead of vfs.libarchive
        xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Addons.SetAddonEnabled","params":{"addonid": "vfs.libarchive", "enabled": false} }')
    else:
        dirs_in_archive = archive_tool.archive_tool(archive_file, directory_to) #Current archive object
    files_in_archive = dirs_in_archive.list_all() #Lists all files in the archive
    file_listing_dict = dirs_in_archive.stat_all() #Dict of all files in the archive containing fullpath, filename, file size (extracted)
    files_extracted, success_of_extraction = dirs_in_archive.extract()  #Extracts all files to directory_out, returns list of files extracted and True/False for extraction success.  Defaults to extract all files in the archive.
    xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Addons.SetAddonEnabled","params":{"addonid": "vfs.libarchive", "enabled": true} }')

    log('---- files_in_archive: %s' % files_in_archive)
    log('---- file_listing_dict: %s' % file_listing_dict)
    log('---- files_extracted: %s' % files_extracted)
    log('---- success_of_extraction: %s' % success_of_extraction)

    return files_extracted, overall_success


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
