#!/usr/bin/env python
#
######################################################################
#
#                  Author: Raymond Jay Bullock
#                  Version: 1.0
#
##################
#
#                  Sumary: 
#                   Manager tool for creating hosts file(s)
#
######################################################################

######################################################################
#
#                 TODO:
#                  - implement:
#
######################################################################

######################################################################
#
#                  imports
#
######################################################################

import os
import sys
import argparse
import traceback
import urllib.request
from subprocess import Popen
from tempfile import NamedTemporaryFile
import mysql.connector as MDB
from mysql.connector import errorcode
from prettytable import from_db_cursor
from prettytable import PrettyTable
from prettytable import PLAIN_COLUMNS
import datetime
import dns.resolver
from pbars import drawSpinner
from pbars import drawProgressBar
from pbars import drawDots
from configparser import SafeConfigParser

######################################################################
#
#                  No changes needed after this line.
# 
######################################################################

# handler for 304 http code
class NotModifiedHandler(urllib.request.BaseHandler):
    def http_error_304(self, req, fp, code, message, headers):
        addinfourl = urllib.request.addinfourl(fp, headers, req.get_full_url())
        addinfourl.code = code
        return addinfourl

# handler for 403 http code
class ProxyBlockedHandler(urllib.request.BaseHandler):
    def http_error_403(self, req, fp, code, message, headers):
        addinfourl = urllib.request.addinfourl(fp, headers, req.get_full_url())
        addinfourl.code = code
        addinfourl.message = message
        return addinfourl

def find_data_file(filename):
    if getattr(sys, 'frozen', False):
        datadir = os.path.dirname(sys.executable)
    else:
        datadir = os.path.dirname(__file__)

    return os.path.join(datadir, filename)

def SetupDB():
    debug(".. Setting up HostDB database\n", 0)
    debug(".... Creating DATABASE '%s'...\n" % DB_NAME, 1)

    sqlcmd = "CREATE DATABASE IF NOT EXISTS %s" % DB_NAME

    cnx.cursor().execute(sqlcmd)

    debug(".... '%s' DATABASE Created\n" % DB_NAME, 1)

    debug("...... Creating TABLES...\n", 1)

    cnx.database = DB_NAME
    cursor = cnx.cursor()

    debug("........ Creating TABLE 'tblDomain'...\n", 2)
    tblcmd = """
        CREATE TABLE IF NOT EXISTS tblDomain (
            IDDomain INT(10) NOT NULL AUTO_INCREMENT PRIMARY KEY,
            Domain VARCHAR(253) NOT NULL UNIQUE KEY,
            Domain_Good BOOLEAN,
            INDEX idx_Domain (Domain),
            INDEX idx_IDDomain (IDDomain))
        """
    cursor.execute(tblcmd)
    debug("........ 'tblDomain' TABLE Created\n", 2)

    debug("........ Creating TABLE 'tblBlackWhite'...\n", 2)
    tblcmd = """
        CREATE TABLE IF NOT EXISTS tblBlackWhite (
            IDBlackWhite INT(10) NOT NULL AUTO_INCREMENT PRIMARY KEY,
            Domain VARCHAR(253) NOT NULL UNIQUE KEY,
            List VARCHAR(6) NOT NULL,
            INDEX idx_Domain (Domain),
            INDEX idx_List (List),
            INDEX idx_IDBlackWhiate (IDBlackWhite))
        """
    cursor.execute(tblcmd)
    debug("........ 'tblBlackWhite' TABLE Created\n", 2)

    debug("........ Creating TABLE 'tblEasylist'...\n", 2)
    tblcmd = """
        CREATE TABLE IF NOT EXISTS tblEasylist (
            IDEasylist INT(10) NOT NULL AUTO_INCREMENT PRIMARY KEY,
            List VARCHAR(253) NOT NULL UNIQUE KEY,
            URL VARCHAR(253) NOT NULL UNIQUE,
            LastModified VARCHAR(30),
            ETag VARCHAR(20),
            INDEX idx_List (List),
            INDEX idx_IDEasylist (IDEasylist))
        """
    cursor.execute(tblcmd)
    debug("........ 'tblEasylist' TABLE Created\n", 2)

    debug("........ Creating TABLE 'tblProvider'...\n", 2)
    tblcmd = """
        CREATE TABLE IF NOT EXISTS tblProvider (
            IDProvider INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            Provider VARCHAR(30) NOT NULL UNIQUE KEY,
            URL VARCHAR(253) NOT NULL UNIQUE,
            Description VARCHAR(100),
            LastModified VARCHAR(30),
            ETag VARCHAR(50),
            INDEX idx_Provider (Provider),
            INDEX idx_IDProvider (IDProvider))
        """
    cursor.execute(tblcmd)
    debug("........ 'tblProvider' TABLE Created\n", 2)

    debug("........ Creating TABLE 'tblHost'...\n", 2)
    tblcmd = """
        CREATE TABLE IF NOT EXISTS tblHost (
            IDHost INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            IDDomain INT NOT NULL,
            IDProvider INT NOT NULL,
            INDEX idx_IDHost (IDHost),
            INDEX idx_IDDomain (IDDomain),
            INDEX idx_IDProvider (IDProvider))
        """
    cursor.execute(tblcmd)
    debug("........ 'tblHost' TABLE Created\n", 2)

    cursor.close()
    debug("...... TABLES Created\n", 1)
    debug(".. Completed HostDB setup\n", 0)    

def AddProvider(provider):
    cnx.database = DB_NAME
    cursor = cnx.cursor()
    
    add_provider = """
        INSERT INTO tblProvider (Provider, URL, Description)
        VALUES (%(Provider)s, %(URL)s, %(Description)s)
        """
    select_provider = """
        SELECT COUNT(*) FROM tblProvider
        WHERE ((Provider = %(Provider)s) AND (URL = %(URL)s))
        """

    debug("DATA: %s\n" % provider, 3)
    debug(".. Adding %s to HostDB\n" % provider["name"], 0)
    debug(".... URL: %s\n.... Description: %s\n" % (provider["url"],provider["description"]), 2)
    data_provider = {
        'Provider': provider["name"],
        'URL': provider["url"],
        'Description': provider["description"],
    }

    # check for duplicate
    cursor.execute(select_provider, data_provider)
    if IsNotDuplicate(cursor.fetchone()):
        cursor.execute(add_provider, data_provider)
        debug(".. %s has been added to provider\'s table\n" % provider["name"], 0)
    else:
        debug(".. %s is a duplicate entry...USE mp instead\n" % provider["name"], 0)

    cnx.commit()
    cursor.close()

def AddBlackWhite(blackwhite):
    cnx.database = DB_NAME
    cursor = cnx.cursor()
    
    add_blackwhite = """
        INSERT INTO tblBlackWhite (Domain, List)
        VALUES (%(Domain)s, %(List)s)
        """
    select_blackwhite = """
        SELECT COUNT(*) FROM tblBlackWhite
        WHERE ((Domain = %(Domain)s))
        """

    debug("DATA: %s\n" % blackwhite, 3)
    debug(".. Adding %s to HostDB\n" % blackwhite["domain"], 0)
    debug(".... List: %s\n" % (blackwhite["list"]), 2)
    data_blackwhite = {
        'Domain': blackwhite['domain'],
        'List': blackwhite['list'],
    }

    # check for duplicate
    cursor.execute(select_blackwhite, data_blackwhite)
    if IsNotDuplicate(cursor.fetchone()):
        cursor.execute(add_blackwhite, data_blackwhite)
        debug(".. %s has been added to black/white\'s table\n" % blackwhite["domain"], 0)
    else:
        debug(".. %s is a duplicate entry...USE mbw instead\n" % blackwhite["domain"], 0)

    cnx.commit()
    cursor.close()

def AddEasylist(easylist):
    cnx.database = DB_NAME
    cursor = cnx.cursor()
    
    add_easylist = """
        INSERT INTO tblEasylist (List, URL)
        VALUES (%(List)s, %(URL)s)
        """
    count_easylist = """
        SELECT COUNT(*) FROM tblEasylist
        WHERE ((List = %(List)s) AND (URL = %(URL)s))
        """

    debug("DATA: %s\n" % easylist, 3)
    debug(".. Adding %s to HostDB\n" % easylist["list"], 0)
    debug(".... URL: %s\n" % (easylist["url"]), 2)
    data_provider = {
        'List': easylist['list'],
        'URL': easylist['url'],
    }

    # check for duplicate
    cursor.execute(count_easylist, data_provider)
    if IsNotDuplicate(cursor.fetchone()):
        cursor.execute(add_easylist, data_provider)
        debug(".. %s has been added to Easylist\'s table\n" % easylist["list"], 0)
    else:
        debug(".. %s is a duplicate entry...USE me instead\n" % easylist["list"], 0)

    cnx.commit()
    cursor.close()

def ModifyProvider(provider):
    cnx.database = DB_NAME
    cursor = cnx.cursor()
    
    select_provider = """
        SELECT IDProvider, Provider, URL, Description, LastModified, ETag FROM tblProvider
        WHERE (Provider = %(Provider)s)
        """

    update_provider = """
        UPDATE tblProvider
        SET URL = %(URL)s,
            Description = %(Description)s,
            LastModified = %(LastModified)s,
            ETag = %(ETag)s
        WHERE (IDProvider = %(IDProvider)s)
        """

    debug("DATA: %s\n" % provider, 3)

    data_provider = {
        'Provider': provider['name'],
    }

    debug(".. Modifying %s in HostDB\n" % provider["name"], 0)

    cursor.execute(select_provider, data_provider)
    if IsNotDuplicate(cursor.fetchone()):
        debug(".. %s was not found...USE ap instead\n" % provider["name"], 0)
    else:
        cursor.execute(select_provider, data_provider)
        for (IDProvider, Provider, URL, Description, LastModified, ETag) in cursor.fetchall():
            debug(".... From:\n.... URL: %s\n.... Description: %s\n.... LastModified: %s\n.... ETag: %s\n" % (URL,Description,LastModified,ETag), 1)
            if provider["url"] == "same": provider["url"] = URL
            if provider["description"] == "same": provider["description"] = Description
            debug(".... To:\n.... URL: %s\n.... Description: %s\n.... LastModified: None\n.... ETag: None\n" % (provider["url"],provider["description"]), 1)

            data_provider = {
                'IDProvider': IDProvider,
                'URL': provider["url"],
                'Description': provider["description"],
                'LastModified': None,
                'ETag': None,
            }
            cursor.execute(update_provider, data_provider)

        debug(".. %s has been modifed in provider\'s table\n" % provider["name"], 0)
        cnx.commit()

    cursor.close()

def ModifyBlackWhite(blackwhite):
    cnx.database = DB_NAME
    cursor = cnx.cursor()
    
    select_blackwhite = """
        SELECT IDBlackWhite, Domain, List FROM tblBlackWhite
        WHERE (Domain = %(Domain)s)
        """

    update_blackwhite = """
        UPDATE tblBlackWhite
        SET Domain = %(Domain)s,
            List = %(List)s,
        WHERE (IDBlackWhite = %(IDBlackWhite)s)
        """

    debug("DATA: %s\n" % provider, 3)

    data_provider = {
        'Domain': blackwhite['domain'],
    }

    debug(".. Modifying %s in HostDB\n" % blackwhite["domain"], 0)

    cursor.execute(select_blackwhite, data_blackwhite)
    if IsNotDuplicate(cursor.fetchone()):
        debug(".. %s was not found...USE abw instead\n" % blackwhite["domain"], 0)
    else:
        cursor.execute(select_blackwhite, data_blackwhite)
        for (IDBlackWhite, Domain, List) in cursor.fetchall():
            debug(".... From:\n.... Domain: %s\n.... List: %s\n" % (Domain,List), 1)
            debug(".... To:\n.... Domain: %s\n.... List: %s\n" % (blackwhite["domain"],blackwhite["list"]), 1)

            data_blackwhite = {
                'IDBlackWhite': IDBlackWhite,
                'Domain': blackwhite["domain"],
                'List': blackwhite["list"],
            }
            cursor.execute(update_provider, data_provider)

        debug(".. %s has been modifed in BlackWhite table\n" % blackwhite["domain"], 0)
        cnx.commit()

    cursor.close()

def ModifyEasylist(easylist):
    cnx.database = DB_NAME
    cursor = cnx.cursor()
    
    select_easylist = """
        SELECT IDEasylist, List, URL, LastModified, ETag FROM tblEasylist
        WHERE (List = %(List)s)
        """

    update_easylist = """
        UPDATE tblList
        SET URL = %(URL)s,
            LastModified = %(LastModified)s,
            ETag = %(ETag)s
        WHERE (IDEasylist = %(IDEasylist)s)
        """

    debug("DATA: %s\n" % easylist, 3)

    data_provider = {
        'List': easylist['list'],
    }

    debug(".. Modifying %s in HostDB\n" % easylist["list"], 0)

    cursor.execute(select_easylist, data_provider)
    if IsNotDuplicate(cursor.fetchone()):
        debug(".. %s was not found...USE ae instead\n" % easylist["list"], 0)
    else:
        cursor.execute(select_easylist, data_provider)
        for (IDEasylist, List, URL, LastModified, ETag) in cursor.fetchall():
            debug(".... From:\n.... URL: %s\n.... LastModified: %s\n.... ETag: %s\n" % (URL,LastModified,ETag), 1)
            if easylist["url"] == "same": easylist["url"] = URL
            debug(".... To:\n.... URL: %s\n.... LastModified: None\n.... ETag: None\n" % easylist["url"], 1)

            data_provider = {
                'IDEasylist': IDEasylist,
                'URL': easylist["url"],
                'LastModified': None,
                'ETag': None,
            }
            cursor.execute(update_easylist, data_provider)

        debug(".. %s has been modifed in easylist\'s table\n" % easylist["list"], 0)
        cnx.commit()

    cursor.close()

def DelProvider(provider):
    cnx.database = DB_NAME
    cursor = cnx.cursor()

    del_provider = """
        DELETE FROM tblProvider
        WHERE ((Provider = %(Provider)s))
        """

    del_host = """
        DELETE host
        FROM tblHost AS host
        LEFT OUTER JOIN tblProvider AS provider
            ON host.IDProvider = provider.IDProvider
        WHERE provider.IDProvider IS NULL
        """
    
    debug("DATA: %s\n" % provider, 3)
    debug(".. Deleting %s from HostDB\n" % provider["name"], 0)
    data_provider = {
        'Provider': provider["name"],
    }

    cursor.execute(del_provider, data_provider)
    cnx.commit()

    # Clean up host
    cursor.execute(del_host)
    debug(".. %s has been deleted from provider\'s table\n" % provider["name"], 0)

    cnx.commit()
    cursor.close()

def DelBlackWhite(blackwhite):
    cnx.database = DB_NAME
    cursor = cnx.cursor()

    del_provider = """
        DELETE FROM tblBlackWhite
        WHERE ((Domain = %(Domain)s))
        """

    debug("DATA: %s\n" % blackwhite, 3)
    debug(".. Deleting %s from HostDB\n" % blackwhite["domain"], 0)
    data_provider = {
        'Domain': blackwhite["domain"],
    }

    cursor.execute(del_provider, data_provider)
    cnx.commit()

    debug(".. %s has been deleted from blackwhite table\n" % blackwhite["domain"], 0)

    cnx.commit()
    cursor.close()

def DelEasylist(easylist):
    cnx.database = DB_NAME
    cursor = cnx.cursor()

    del_easylist = """
        DELETE FROM tblEasylist
        WHERE ((List = %(List)s))
        """

    debug("DATA: %s\n" % easylist, 3)
    debug(".. Deleting %s from HostDB\n" % easylist["list"], 0)
    data_provider = {
        'List': easylist["list"],
    }

    cursor.execute(del_easylist, data_provider)
    cnx.commit()

    debug(".. %s has been deleted from easylist\'s table\n" % easylist["list"], 0)

    cnx.commit()
    cursor.close()

def ListProviders():
    cnx.database = DB_NAME
    cursor = cnx.cursor()

    debug(".. List of Providers\n\n", 0)

    cursor.execute("SELECT Provider, URL, Description, LastModified, ETag FROM tblProvider")
    
    ptable = from_db_cursor(cursor)
    ptable.align["Provider"] = "l"
    ptable.align["URL"] = "l"
    ptable.align["Description"] = "l"
    ptable.align["LastModified"] = "l"
    ptable.align["ETag"] = "l"
    ptable.sortby = "Provider"
    ptable.set_style(PLAIN_COLUMNS)
    print(ptable)
    cursor.close()
    
def ListBlackWhite():
    cnx.database = DB_NAME
    cursor = cnx.cursor()

    debug(".. List of Black/White domains\n\n", 0)

    cursor.execute("SELECT Domain, List FROM tblBlackWhite")
    
    ptable = from_db_cursor(cursor)
    ptable.align["Domain"] = "l"
    ptable.align["List"] = "l"
    ptable.sortby = "List"
    ptable.set_style(PLAIN_COLUMNS)
    print(ptable)
    cursor.close()

def ListEasylist():
    cnx.database = DB_NAME
    cursor = cnx.cursor()

    debug(".. List of Easylists\n\n", 0)

    cursor.execute("SELECT List, URL, LastModified, ETag FROM tblEasylist")
    
    ptable = from_db_cursor(cursor)
    ptable.align["List"] = "l"
    ptable.align["URL"] = "l"
    ptable.align["LastModified"] = "l"
    ptable.align["ETag"] = "l"
    ptable.sortby = "List"
    ptable.set_style(PLAIN_COLUMNS)
    print(ptable)
    cursor.close()
    
def LineCount(filename):
    f = open(filename, "r")
    lines = 0
    buf_size = 1024 * 1024
    read_f = f.read # loop optimization

    buf = read_f(buf_size)
    while buf:
        lines += buf.count('\n')
        lines += buf.count('\r')
        buf = read_f(buf_size)

    f.close()
    
    return lines

def HostValReport():
    cnx.database = DB_NAME
    cursor = cnx.cursor()
    hostcurs = cnx.cursor()

    count_host = """
        SELECT COUNT(*) FROM tblHost
        WHERE IDProvider = %(IDProvider)s
        """

    count_false = """
        SELECT COUNT(*) FROM tblDomain
        WHERE Domain_Good = False
        AND IDDomain IN (
            SELECT IDDomain FROM tblHost
            WHERE IDProvider = %(IDProvider)s)
        """

    count_true = """
        SELECT COUNT(*) FROM tblDomain
        WHERE Domain_Good = True
        AND IDDomain IN (
            SELECT IDDomain FROM tblHost
            WHERE IDProvider = %(IDProvider)s)
        """

    count_null = """
        SELECT COUNT(*) FROM tblDomain
        WHERE Domain_Good IS NULL
        AND IDDomain IN (
            SELECT IDDomain FROM tblHost
            WHERE IDProvider = %(IDProvider)s)
        """

    count_domain = """
        SELECT COUNT(*) FROM tblDomain
        """

    count_domain_false = """
        SELECT COUNT(*) FROM tblDomain
        WHERE Domain_Good = False
        """

    count_domain_true = """
        SELECT COUNT(*) FROM tblDomain
        WHERE Domain_Good = True
        """

    count_domain_null = """
        SELECT COUNT(*) FROM tblDomain
        WHERE Domain_Good IS NULL
        """

    select_provider = """
        SELECT IDProvider, Provider FROM tblProvider
        """

    debug(".. Host Validation Report ...\n\n", 0)

    report = PrettyTable(["Provider", "Host Count", "DNS Passed", "DNS Failed", "Percent", "Not Checked"])
    report.align["Provider"] = "l"
    report.align["Host Count"] = "r"
    report.align["DNS Passed"] = "r"
    report.align["DNS Failed"] = "r"
    report.align["Percent"] = "r"
    report.align["Not Checked"] = "r"

    cursor.execute(select_provider)
    for IDProvider, Provider in cursor.fetchall():
        data_provider = {
            'IDProvider': IDProvider,
        }
        hostcurs.execute(count_host, data_provider)
        host_total = hostcurs.fetchone()[0]
        hostcurs.execute(count_true, data_provider)
        host_pass = hostcurs.fetchone()[0]
        hostcurs.execute(count_false, data_provider)
        host_fail = hostcurs.fetchone()[0]
        host_percent = int(round((host_fail / host_total) * 100))
        hostcurs.execute(count_null, data_provider)
        host_check = hostcurs.fetchone()[0]

        report.add_row([Provider,host_total,host_pass,host_fail,"%s%%" % host_percent,host_check])

    report.sortby = "Provider"
    report.set_style(PLAIN_COLUMNS)
    report.sortby = None
    hostcurs.execute(count_domain)
    total_host = hostcurs.fetchone()[0]
    hostcurs.execute(count_domain_true)
    total_pass = hostcurs.fetchone()[0]
    hostcurs.execute(count_domain_false)
    total_fail = hostcurs.fetchone()[0]
    hostcurs.execute(count_domain_null)
    total_check = hostcurs.fetchone()[0]
    report.add_row(["", "", "", "", "", ""])
    report.add_row(["All Domains", total_host, total_pass, total_fail, "%s%%" % int(round((total_fail / total_host) * 100)), total_check])
    print(report)

    debug("\n.. End Host Validation Report\n", 0)
    hostcurs.close()
    cursor.close()
    
def HostVal(ResetDomain = False):
    cnx.database = DB_NAME
    cursor = cnx.cursor()
    update = cnx.cursor()

    count_domain = """
        SELECT COUNT(*) FROM tblDomain
        WHERE Domain_Good IS NULL
        """

    select_domain = """
        SELECT IDDomain, Domain FROM tblDomain
        WHERE Domain_Good IS NULL
        LIMIT 5000
        """

    update_domain = """
        UPDATE tblDomain
        SET Domain_Good = %(Domain_Good)s
        WHERE IDDomain = %(IDDomain)s
        """

    reset_check = """
        UPDATE tblDomain
        SET Domain_Good = NULL
        """

    debug(".. Host Validation starting ...\n", 0)

    ResetDomain = ResetDomain["reset"]

    debug(".... ResetDomain: %s\n" % ResetDomain, 3)
    if ResetDomain == "True":
        debug(".... Reset Validations ...\n", 1)
        update.execute(reset_check)
    else:
        cursor.execute(count_domain)
        domain_count = cursor.fetchone()[0]
        if domain_count > 5000: domain_count = 5000
        domain_checked = 1
        debug(".... Domain Count: %s\n" % domain_count, 2)

        spinner = 1
        cursor.execute(select_domain)
        resolver = dns.resolver.Resolver()
        resolver.timeout = 10.0
        resolver.lifetime = 10.0
        for IDDomain, Domain in cursor.fetchall():
            try:
                answer = resolver.query(Domain)
                data_provider = {
                    'IDDomain': IDDomain,
                    'Domain_Good': True
                }
            except:
                data_provider = {
                    'IDDomain': IDDomain,
                    'Domain_Good': False
                }
            update.execute(update_domain, data_provider)
            spinner = drawSpinner(spinner)
            drawProgressBar(float(domain_checked / domain_count), 50, 'c')
            debug(" Domains Checked: %s Domain: %s     " % (domain_checked,Domain), 3)
            debug("\r", 0)
            domain_checked += 1
        
        if DBG < 3:
            debug("\r{0}\r".format(" "*60), 0)
        else:
            debug("\n", 3)

    debug(".. Validation complete\n", 0)
    cnx.commit()
    cursor.close()
    update.close()
    HostValReport()

# checked of duplicate found
def IsNotDuplicate(reccount):
    if reccount == None:
        return True
    elif reccount[0] == 0:
        return True
    else:
        return False

# provide touch functionality
def touch(path):
    if not os.path.exists(os.path.dirname(path)):
        os.makedirs(os.path.dirname(path))
    with open(path, 'a'):
        os.utime(path, None)

# provide different levels of print with formating functions
def debug(msg, level):
    if DBG >= level:
        sys.stdout.write("{0}".format(msg))

def MakeSEDClean(REs):
    tmp_clean = NamedTemporaryFile(delete=False, mode="w")
    for res in REs:
        tmp_clean.write("%s\n" % res)
    return tmp_clean.name

def OpenTempFile():
    open_tmp_file = NamedTemporaryFile(delete=False)
    return open_tmp_file.name
    
def DownloadHostFiles():
    debug(".. Downloading Hosts Started ...\n", 0)

    cnx.database = DB_NAME
    provcurs = cnx.cursor()
    hostcurs = cnx.cursor()

    select_provider = """
        SELECT IDProvider, Provider, URL, LastModified, ETag FROM tblProvider
        """

    update_provider = """
        UPDATE tblProvider
        SET LastModified = %(LastModified)s,
            ETag = %(ETag)s
        WHERE (IDProvider = %(IDProvider)s)
        """

    add_domain = """
        INSERT INTO tblDomain (Domain)
        VALUES (%(Domain)s)
        """
    
    count_domain = """
        SELECT COUNT(*) FROM tblDomain
        WHERE (Domain = %(Domain)s)
        """

    select_domain = """
        SELECT IDDomain FROM tblDomain
        WHERE (Domain = %(Domain)s)
        """
    
    del_domain = """
        DELETE domain
        FROM tblDomain AS domain
        LEFT OUTER JOIN tblHost AS host
            ON host.IDDomain = domain.IDDomain
        WHERE host.IDDomain IS NULL
        """
    
    count_host = """
        SELECT COUNT(*) FROM tblHost
        WHERE (IDDomain = %(IDDomain)s AND IDProvider = %(IDProvider)s)
        """

    add_host = """
        INSERT INTO tblHost (IDProvider, IDDomain)
        VALUES (%(IDProvider)s, %(IDDomain)s)
        """

    del_host = """
        DELETE FROM tblHost
        WHERE ((IDProvider = %(IDProvider)s))
        """
    provcurs.execute(select_provider)
    
    for (IDProvider, Provider, URL, LastModified, ETag) in provcurs.fetchall():
        debug("Data Returned: IDProvider: %s Provider: %s URL: %s LastModified: %s ETag: %s\n" %(IDProvider, Provider, URL, LastModified, ETag), 3)
        if BYPASSPROXY:
            proxy_handler = urllib.request.ProxyHandler(proxies=None)
            opener = urllib.request.build_opener(ProxyBlockedHandler(), proxy_handler)
        else:
            opener = urllib.request.build_opener(ProxyBlockedHandler())

        urllib.request.install_opener(opener)

        req = urllib.request.Request(URL)
        url_handle = opener.open(req)
        if hasattr(url_handle, 'code') and url_handle.code == 403:
            # URL blocked by proxy
            debug(".... %s Provider's url %s\n" % (Provider,url_handle.message), 1)
            continue
        headers = url_handle.info()
        headETag = headers.get("ETag")
        headLastModified = headers.get("Last-Modified")

        if ETag:
            req.add_header("IF-None-Match", ETag)
        if LastModified:
            req.add_header("If-Modified-Since", LastModified)

        opener = urllib.request.build_opener(NotModifiedHandler(), ProxyBlockedHandler())
        url_handle = opener.open(req)
        headers = url_handle.info()
        debug("%s\n" % headers, 3)
        if hasattr(url_handle, 'code') and url_handle.code == 304:
            # Not updated: no need to download
            debug(".... %s Provider's host file upto date, skipping\n" % Provider, 1)
            continue

        # Updated: process download
        debug(".... %s Downloading Provider's host file\n" % Provider, 1)

        data_provider = {
            'IDProvider': IDProvider,
        }
    
        hostcurs.execute(del_host, data_provider)
        cnx.commit

        file_size = headers.get("Content-Length")
        debug("File Size: %s\n" % file_size, 3)
        if file_size: file_size = int(file_size)
        file_size_dl = 0
        block_sz = 8192

        tmp_host = OpenTempFile()
        tmp_handle = open(tmp_host, 'wb')            

        while True:
            if file_size:
                drawProgressBar(float(file_size_dl / file_size), 50, 'c')
                debug("\r", 0)
            buffer = url_handle.read(block_sz)
            if not buffer:
                break

            file_size_dl += len(buffer)
            tmp_handle.write(buffer)

        if DBG < 3:
            debug("\r{0}\r".format(" "*60), 0)
        else:
            debug("\n", 3)

        tmp_handle.close()
        url_handle.close()

        debug("...... Processing Host file\n", 2)

        # Remove IP information, comments, spaces and blank lines
        debug("........ Starting Host Cleanup\n", 3)
        REs = ["s/\\([0-9]\\{1,3\\}\\.\\)\\{3,3\\}[0-9]\\{1,3\\}//g"]
        REs.append("/localhost/d")
        REs.append("s:#.*$::g")
        REs.append("s/^[ \\t]*//")
        REs.append("s/[ \\t]*$//")
        REs.append("s/\\r//")
        REs.append("/^$/d")
        retclean = MakeSEDClean(REs)
        ret = Popen(["sed.exe", "-i", "-f", retclean, tmp_host],stdout=open(os.devnull,"w"), stderr=open(os.devnull,"w")).communicate()[0]
        os.remove(retclean)

        host_size = LineCount(tmp_host)
        host_size_p = 0

        debug("TempHostFile: %s\n" % tmp_host, 3)
        tmp_handle = open(tmp_host, 'r')
        for fline in tmp_handle:
            drawProgressBar(float(host_size_p / host_size), 50, 'c')
            debug("\r", 0)
            host_size_p += 1
            debug("file_size: %s file_size_p: %s\r" % (host_size,host_size_p), 3)

            data_provider = {
                'Domain': fline.strip("\n"),
            }
                
            hostcurs.execute(count_domain, data_provider)
            if IsNotDuplicate(hostcurs.fetchone()):
                hostcurs.execute(add_domain, data_provider)
                data_provider = {
                    'IDProvider': IDProvider,
                    'IDDomain': hostcurs.lastrowid
                }
            else:
                hostcurs.execute(select_domain, data_provider)
                for IDDomain in hostcurs.fetchall():
                    data_provider = {
                        'IDProvider': IDProvider,
                        'IDDomain': IDDomain[0]
                    }
            hostcurs.execute(count_host, data_provider)
            if IsNotDuplicate(hostcurs.fetchone()):
                hostcurs.execute(add_host, data_provider)
            
        if DBG < 3:
            debug("\r{0}\r".format(" "*60), 0)
        else:
            debug("\n", 3)

        tmp_handle.close()
        cnx.commit()
        debug("...... Processing Complete\n", 2)

        if DBG < 3:
            os.remove(tmp_host)

        debug("...... Cleaning Up\n", 2)
        # clean up domain table
        hostcurs.execute(del_domain)
        cnx.commit
        debug("...... Clean Up complete\n", 2)

        data_provider = {
            'IDProvider': IDProvider,
            'LastModified': headLastModified,
            'ETag': headETag,
        }
        hostcurs.execute(update_provider, data_provider)
        cnx.commit()
        debug(".... Download Completed ...\n", 1)

    debug(".. Downloading Hosts Completed\n", 0)

def DownloadEasylistFiles():
    debug(".. Downloading Easylist Started ...\n", 0)

    cnx.database = DB_NAME
    listcurs = cnx.cursor()
    urlcurs = cnx.cursor()

    select_easylist = """
        SELECT IDEasylist, List, URL, LastModified, ETag FROM tblEasylist
        """

    update_easylist = """
        UPDATE tblEasylist
        SET LastModified = %(LastModified)s,
            ETag = %(ETag)s
        WHERE (IDEasylist = %(IDEasylist)s)
        """

    listcurs.execute(select_easylist)
    
    for (IDEasylist, List, URL, LastModified, ETag) in listcurs.fetchall():
        debug("Data Returned: IDEasylist: %s List: %s URL: %s LastModified: %s ETag: %s\n" %(IDEasylist, List, URL, LastModified, ETag), 3)
        if BYPASSPROXY:
            proxy_handler = urllib.request.ProxyHandler(proxies=None)
            opener = urllib.request.build_opener(ProxyBlockedHandler(), proxy_handler)
        else:
            opener = urllib.request.build_opener(ProxyBlockedHandler())

        urllib.request.install_opener(opener)

        req = urllib.request.Request(URL)
        url_handle = opener.open(req)
        if hasattr(url_handle, 'code') and url_handle.code == 403:
            # URL blocked by proxy
            debug(".... %s List's url %s\n" % (List,url_handle.message), 1)
            continue
        headers = url_handle.info()
        headETag = headers.get("ETag")
        headLastModified = headers.get("Last-Modified")

        if ETag:
            req.add_header("IF-None-Match", ETag)
        if LastModified:
            req.add_header("If-Modified-Since", LastModified)

        opener = urllib.request.build_opener(NotModifiedHandler(), ProxyBlockedHandler())
        url_handle = opener.open(req)
        headers = url_handle.info()
        debug("%s\n" % headers, 3)
        if hasattr(url_handle, 'code') and url_handle.code == 304:
            # Not updated: no need to download
            debug(".... %s List's file upto date, skipping\n" % List, 1)
            continue

        # Updated: process download
        debug(".... %s Downloading List's file\n" % List, 1)

        data_provider = {
            'IDEasylist': IDEasylist,
        }
    
        file_size = headers.get("Content-Length")
        debug("File Size: %s\n" % file_size, 3)
        if file_size: file_size = int(file_size)
        file_size_dl = 0
        block_sz = 8192

        tmp_list = OpenTempFile()
        debug("TempFile: %s\n" % tmp_list, 3)
        tmp_handle = open(tmp_list, 'wb')            

        while True:
            if file_size: drawProgressBar(float(file_size_dl / file_size), 50, 'c')
            debug("\r", 0)
            buffer = url_handle.read(block_sz)
            if not buffer:
                break

            file_size_dl += len(buffer)
            tmp_handle.write(buffer)

        if DBG < 3:
            debug("\r{0}\r".format(" "*60), 0)
        else:
            debug("\n", 3)

        tmp_handle.close()
        url_handle.close()

        # Verify is an adblock list
        tmp_handle = open(tmp_list, "r")
        tmp_list_adblock = False
        fline = tmp_handle.read()
        if not fline.rfind("[Adblock Plus"):
            tmp_list_adblock = True
        tmp_handle.close()
            
        # Convert to Privoxy
        if tmp_list_adblock:
            debug("........ Starting Adblock -> Easylist Conversion\n", 1)
            debug(".......... Creating Action file for %s\n" % List, 2)
            action_handle = open("%s/%s.action" % (CONFDIR, List), "wt")
            action_handle.write("{ +block{%s} }\n" % List)
            action_handle.close()
            action_handle = open("%s/%s.error" % (CONFDIR, List), "wt")
            action_handle.close
            REs = ["/^!.*/d"]
            REs.append("1,1 d")
            REs.append("/^@@.*/d")
            REs.append("/\\$.*/d")
            REs.append("/#/d")
            REs.append("s/\\./\\\\./g")
            REs.append("s/\\?/\\\\?/g")
            REs.append("s/\\*/.*/g")
            REs.append("s/(/\\\\(/g")
            REs.append("s/)/\\\\)/g")
            REs.append("s/\\[/\\\\[/g")
            REs.append("s/\\]/\\\\]/g")
            REs.append("s/\\^/[\\/\\&:\\?=_]/g")
            REs.append("s/^||/\\./g")
            REs.append("s/^|/^/g")
            REs.append("s/|$/\\$/g")
            REs.append("/|/d")
            retclean = MakeSEDClean(REs)
            ret = Popen(["sed.exe", "-f", retclean, tmp_list],stdout=open("%s/%s.action" % (CONFDIR, List), "at"), stderr=open("%s/%s.error" % (CONFDIR, List))).communicate()[0]
            os.remove(retclean)
            action_handle = open("%s/%s.action" % (CONFDIR, List), "at")
            action_handle.write("{ +filter{%s} }\n*\n{ -block }\n" % List)
            action_handle.close()
            action_handle = open("%s/%s.error" % (CONFDIR, List), "at")
            action_handle.close
            REs = ["/^@@.*/!d"]
            REs.append("s/^@@//g")
            REs.append("/\\$.*/d")
            REs.append("/#/d")
            REs.append("s/\\./\\\\./g")
            REs.append("s/\\?/\\\\?/g")
            REs.append("s/\\*/.*/g")
            REs.append("s/(/\\\\(/g")
            REs.append("s/)/\\\\)/g")
            REs.append("s/\\[/\\\\[/g")
            REs.append("s/\\]/\\\\]/g")
            REs.append("s/\\^/[\\/\\&:\\?=_]/g")
            REs.append("s/^||/\\./g")
            REs.append("s/^|/^/g")
            REs.append("s/|$/\\$/g")
            REs.append("/|/d")
            retclean = MakeSEDClean(REs)
            ret = Popen(["sed.exe", "-f", retclean, tmp_list],stdout=open("%s/%s.action" % (CONFDIR, List), "at"), stderr=open("%s/%s.error" % (CONFDIR, List))).communicate()[0]
            os.remove(retclean)
            action_handle = open("%s/%s.action" % (CONFDIR, List), "at")
            action_handle.write("{ -block +handle-as-image }\n")
            action_handle.close()
            action_handle = open("%s/%s.error" % (CONFDIR, List), "at")
            action_handle.close
            REs = ["/^@@.*/!d"]
            REs.append("s/^@@//g")
            REs.append("/\\$.*image.*/!d")
            REs.append("s/\\$.*image.*//g")
            REs.append("/#/d")
            REs.append("s/\\./\\\\./g")
            REs.append("s/\\?/\\\\?/g")
            REs.append("s/\\*/.*/g")
            REs.append("s/(/\\\\(/g")
            REs.append("s/)/\\\\)/g")
            REs.append("s/\\[/\\\\[/g")
            REs.append("s/\\]/\\\\]/g")
            REs.append("s/\\^/[\\/\\&:\\?=_]/g")
            REs.append("s/^||/\\./g")
            REs.append("s/^|/^/g")
            REs.append("s/|$/\\$/g")
            REs.append("/|/d")
            retclean = MakeSEDClean(REs)
            ret = Popen(["sed.exe", "-f", retclean, tmp_list],stdout=open("%s/%s.action" % (CONFDIR, List), "at"), stderr=open("%s/%s.error" % (CONFDIR, List))).communicate()[0]
            os.remove(retclean)

            debug(".......... Creating Filter file for %s\n" % List, 2)
            filter_handle = open("%s/%s.filter" % (CONFDIR, List), "wt")
            filter_handle.write("FILTER: %s Tag filter of %s\n" % (List,List))
            filter_handle.close
            filter_handle = open("%s/%s.error" % (CONFDIR, List), "at")
            filter_handle.close
            REs = ["/^#/!d"]
            REs.append("s/^##//g")
            REs.append("s/^#\\(.*\\)\\[.*\\]\\[.*\\]*/s|<([a-zA-Z0-9]+)\\\\s+.*id=.?\\1.*>.*<\\/\\\\1>||g/g")
            REs.append("s/^#\\(.*\\)/s|<([a-zA-Z0-9]+)\\\\s+.*id=.?\\1.*>.*<\\/\\\\1>||g/g")
            REs.append("s/^\\.\\(.*\\)/s|<([a-zA-Z0-9]+)\\\\s+.*class=.?\\1.*>.*<\\/\\\\1>||g/g")
            REs.append("s/^a\\[\\(.*\\)\\]/s|<a.*\\1.*>.*<\\/a>||g/g")
            REs.append("s/^\\([a-zA-Z0-9]*\\)\\.\\(.*\\)\\[.*\\]\\[.*\\]*/s|<\\1.*class=.?\\2.*>.*<\\/\\1>||g/g")
            REs.append("s/^\\([a-zA-Z0-9]*\\)#\\(.*\\):.*[:[^:]]*[^:]*/s|<\\1.*id=.?\\2.*>.*<\\/\\1>||g/g")
            REs.append("s/^\\([a-zA-Z0-9]*\\)#\\(.*\\)/s|<\\1.*id=.?\\2.*>.*<\\/\\1>||g/g")
            REs.append("s/^\\[\\([a-zA-Z]*\\).=\\(.*\\)\\]/s|\\1^=\\2>||g/g")
            REs.append("s/\\^/[\\/\\&:\\?=_]/g")
            REs.append("s/\\.\\([a-zA-Z0-9]\\)/\\\\.\\1/g")
            retclean = MakeSEDClean(REs)
            ret = Popen(["sed.exe", "-f", retclean, tmp_list],stdout=open("%s/%s.filter" % (CONFDIR, List), "at"), stderr=open("%s/%s.error" % (CONFDIR, List))).communicate()[0]
            os.remove(retclean)

            debug("...... Processing Complete\n", 2)
        else:
            debug("...... Skipping easylist file, not an Adblock list\n", 2)

        if DBG < 3:
            os.remove(tmp_list)

        data_provider = {
            'IDEasylist': IDEasylist,
            'LastModified': headLastModified,
            'ETag': headETag,
        }
        if DBG < 3:
            urlcurs.execute(update_easylist, data_provider)
            cnx.commit()

        debug(".... Download Completed ...\n", 1)

    debug(".. Downloading Easylist Completed\n", 0)
    urlcurs.close()
    listcurs.close()

def CreateHost(hosttype):
    cnx.database = DB_NAME
    cursor = cnx.cursor()

    host_select_domain = """
        SELECT Domain FROM tblDomain
        WHERE Domain_Good IS NOT False AND Domain NOT IN (
            SELECT Domain FROM tblBlackWhite
            WHERE List = 'white' )
        UNION
        SELECT Domain FROM tblBlackWhite
        WHERE (List != 'white')
        """

    provider_select_domain = """
        SELECT Domain FROM tblDomain
        WHERE Domain_Good IS NOT False
        AND IDDomain = %(IDDomain)s
        AND Domain NOT IN (
            SELECT Domain FROM tblBlackWhite
            WHERE List = 'white' )
        """
    provider_select_blackwhite = """
        SELECT Domain FROM tblBlackWhite
        WHERE (List != 'white')
        AND Domain NOT IN (
            SELECT Domain FROM tblDomain )
        """

    provider_select_host = """
        SELECT IDDomain FROM tblHost
        WHERE IDProvider = %(IDProvider)s
        """

    count_domain = """
        SELECT COUNT(*) FROM tblDomain
        WHERE Domain_Good IS NOT False AND Domain NOT IN (
            SELECT Domain FROM tblBlackWhite
            WHERE List = 'white' )
        """

    provider_count_domain = """
        SELECT COUNT(*) FROM tblDomain
        WHERE Domain_Good IS NOT False
        AND IDDomain IN (
            SELECT IDDomain FROM tblHost
            WHERE IDProvider = %(IDProvider)s )
        AND Domain NOT IN (
            SELECT Domain FROM tblBlackWhite
            WHERE List = 'white' )
        """

    count_blacklist = """
        SELECT COUNT(*) FROM tblBlackWhite
        WHERE (List != 'white')
        """

    select_provider = """
        SELECT IDProvider, Provider FROM tblProvider
        """

    debug("DATA: %s\n" % hosttype, 3)
    debug(".. Creating Hosts File Started ...\n", 0)

    # hosts: ipaddr domain
    if hosttype['type'] == 'host':
        cursor.execute(count_domain)
        domain_count = cursor.fetchone()[0]
        cursor.execute(count_blacklist)
        domain_count += cursor.fetchone()[0]
        domain_p = 1

        host_file = open("%s/HOSTS" % CONFDIR, "w")
        debug(".... Creating: %s/HOSTS ...\n" % CONFDIR, 1)
        debug("...... Domain Count: %s\n" % domain_count, 2)
        
        host_file.write("# Generated by HostDB\n# Generated on %s\n" % datetime.date.today())
        cursor.execute(host_select_domain)
        for domain in cursor.fetchall():
            host_file.write("%s %s\n" % (hosttype['ipaddr'], domain[0]))
            drawProgressBar(float(domain_p / domain_count), 50, 'c')
            domain_p += 1
            debug("\r", 0)

        if DBG < 3:
            debug("\r{0}\r".format(" "*60), 0)
        else:
            debug("\n", 3)

        debug(".... Creating HOSTS completed\n", 1)
        host_file.close()

    # dnsmasq: "address=/domain/ipaddr
    if hosttype['type'] == 'dnsmasq':
        cursor.execute(count_domain)
        domain_count = cursor.fetchone()[0]
        cursor.execute(count_blacklist)
        domain_count += cursor.fetchone()[0]
        domain_p = 1

        host_file = open("%s/dnsmasq.custom" % CONFDIR, "w")
        debug(".... Creating: %s/dnsmasq.custom ...\n" % CONFDIR, 1)
        debug("...... Domain Count: %s\n" % domain_count, 2)
        
        host_file.write("# Generated by HostDB\n# Generated on %s\n" % datetime.date.today())
        cursor.execute(host_select_domain)
        for domain in cursor.fetchall():
            host_file.write("address=/%s/%s\n" % (domain[0], hosttype['ipaddr']))
            drawProgressBar(float(domain_p / domain_count), 50, 'c')
            debug("\r", 0)
            domain_p += 1

        if DBG < 3:
            debug("\r{0}\r".format(" "*60), 0)
        else:
            debug("\n", 3)

        debug(".... Creating dnsmasq.custom completed\n", 1)
        host_file.close()

    # privoxy: header -> domains
    #Header: { +block{HostDB Provider} +handle-as-image }
    if hosttype['type'] == 'privoxy':
        hostcurs = cnx.cursor()
        domaincurs = cnx.cursor()
        cursor.execute(select_provider)
        for IDProvider, Provider in cursor.fetchall():
            host_file = open("%s/%s.action" % (CONFDIR,Provider), "w")
            debug(".... Creating %s/%s.action ...\n" % (CONFDIR,Provider), 1)
            debug("...... IDProvider: %s Provider: %s\n" % (IDProvider, Provider), 3)

            data_provider = {
                'IDProvider': IDProvider
            }
            cursor.execute(provider_count_domain, data_provider)
            domain_count = cursor.fetchone()[0]
            cursor.execute(count_blacklist)
            domain_count += cursor.fetchone()[0]
            domain_p = 1
            debug("...... Domain Count: %s\n" % domain_count, 2)

            host_file.write("# Generated by HostDB\n# Generated on %s\n" % datetime.date.today())
            host_file.write("{ +block{HostDB %s} }\n" % Provider)

            hostcurs.execute(provider_select_host, data_provider)
            for IDDomain in hostcurs.fetchall():
                data_provider = {
                    'IDDomain': IDDomain[0]
                }
                domaincurs.execute(provider_select_domain, data_provider)
                for domain in domaincurs.fetchall():
                    domainsetup = domain[0]
                    domainsetup = domainsetup.replace(".", "\.")
                    domainsetup = domainsetup.replace("-", "\-")
                    host_file.write("%s\n" % domainsetup)

                    drawProgressBar(float(domain_p / domain_count), 50, 'c')
                    domain_p += 1
                    debug("\r", 0)
                
            hostcurs.execute(provider_select_blackwhite)
            for Domain in hostcurs.fetchall():
                host_file.write("%s\n" % domain[0])
                drawProgressBar(float(domain_p / domain_count), 50)
                domain_p += 1
                debug("\r", 0)
                
            if DBG < 3:
                debug("\r{0}\r".format(" "*60), 0)
            else:
                debug("\n", 3)

            debug(".... Creating %s.action completed\n" % Provider, 1)
            host_file.close()

        domaincurs.close()
        hostcurs.close()

        DownloadEasylistFiles()

    debug(".. Creating Hosts File Completed\n", 0)
    cursor.close()

def main():
    debug("HostDB starting...\n\n", 0)

    # build command without optionals
    options = {i:str(vars(args)[i]).strip("[]'") for i in vars(args) if i in
               ["name", "url", "description", "type", "ipaddr", "domain", "list", "reset"]}
    debug("Options: %s Len: %s\n" % (options, len(options)), 3)

    if len(options) > 0:
        globals()[args.func](options)
    else:
        globals()[args.func]()
    
    debug("\nHostDB completed\n", 0)

######################################################################
#
#                  script variables
#
######################################################################

config = SafeConfigParser()
config.read(find_data_file("HostDB.ini"))
CONFDIR = config.get("PATHS","CONFIG")
if getattr(sys, 'frozen', False):
    TMPNAME = os.path.splitext(os.path.basename(sys.executable))[0]
else:
    TMPNAME = os.path.splitext(os.path.basename(__file__))[0]
BYPASSPROXY = config.getboolean("SECURITY","BYPASSPROXY")

# check whether an instance is already running
if os.path.isfile("%s/%s.lock" % (CONFDIR,TMPNAME)):
    print("An Instance of {0} is already running. Exit".format(TMPNAME))
    sys.exit(1)

parser = argparse.ArgumentParser(prog='HostDB',description='Manager tool for hosts file(s)',
                                 formatter_class=argparse.RawTextHelpFormatter)

# Optional options
parser.add_argument("-v", metavar="#",
                    nargs=1,
                    default=[config.getint("OPTIONS", "VERBOSITY")],
                    choices=[0,1,2,3],
                    help="Set level of messages, where\n"
                        "    0: Normal Output\n"
                        "    1: A little more information\n"
                        "    2: All information\n"
                        "    3: Developer use for displaying debug information",
                    action="store", dest="verbosity",
                    type=int)
parser.add_argument("-ver", "--version",
                    action="version",
                    version='%(prog)s v1.0')

# Optional Connection Specific options
secure = parser.add_argument_group('Connection', 'Optional connection information')
secure.add_argument("-u",
                    nargs=1,
                    default=[config.get("SECURITY", "USER")],
                    help="Set the user to use",
                    action="store", dest="user")
secure.add_argument("-p",
                    nargs=1,
                    default=[""],
                    help="Set the password to use",
                    action="store", dest="password")
secure.add_argument("-ho",
                    nargs=1,
                    default=[config.get("SECURITY", "HOST")],
                    help="Set the host to use",
                    action="store", dest="host")

# Command Options, only one can be used
commands = parser.add_subparsers(title="Command",
                                 description="valid commands",
                                 help="additional help and exit")

cmd_downloadhost = commands.add_parser("dh", help="Dowload the host files from the providers if it has been updated.")
cmd_downloadhost.set_defaults(func="DownloadHostFiles")

cmd_downloadeasylist = commands.add_parser("ce", help="Create the easylist files if it has been updated.")
cmd_downloadeasylist.set_defaults(func="DownloadEasylistFiles")

cmd_createhost = commands.add_parser("ch", help="Create a host file",
                            formatter_class=argparse.RawTextHelpFormatter)
cmd_createhost.set_defaults(func="CreateHost")
cmd_createhost.add_argument("type",
                    nargs=1,
                    choices=['host','dnsmasq','privoxy'],
                    action='store',
                    help="Type of host file to create. Where:\n"
                        "   host: Create a standard windows type host")
cmd_createhost.add_argument('-ipaddr',
                            nargs=1,
                            default=['127.0.0.1'],
                            action='store',
                            help="What IP Address to use in the host file redirection\n"
                                "   Default: 127.0.0.1")

cmd_listblackwhite = commands.add_parser("lbw", help="List current black/white listed domains")
cmd_listblackwhite.set_defaults(func="ListBlackWhite")

cmd_listprovider = commands.add_parser("lp", help="List all current providers")
cmd_listprovider.set_defaults(func="ListProviders")

cmd_listeasylist = commands.add_parser("le", help="List all current easylist")
cmd_listeasylist.set_defaults(func="ListEasylist")

cmd_setup = commands.add_parser("setup", help="Setup hostdb database")
cmd_setup.set_defaults(func="SetupDB")

cmd_addprovider = commands.add_parser("ap", help="Add a provider of host list")
cmd_addprovider.set_defaults(func="AddProvider")
cmd_addprovider.add_argument("name",
                            nargs=1,
                            action="store",
                            help="Name of the provider")
cmd_addprovider.add_argument("url",
                            nargs=1,
                            action="store",
                            help="URL of the provider's host file")
cmd_addprovider.add_argument("description",
                            nargs=1,
                            action="store",
                            help="Description of the provider")

cmd_modifyprovider = commands.add_parser("mp", help="Modify a provider of host list")
cmd_modifyprovider.set_defaults(func="ModifyProvider")
cmd_modifyprovider.add_argument("name",
                            nargs=1,
                            action="store",
                            help="Name of the provider to modify")
cmd_modifyprovider.add_argument("url",
                            nargs=1,
                            action="store",
                            help="URL of the provider's host file: same = do not update")
cmd_modifyprovider.add_argument("description",
                            nargs=1,
                            action="store",
                            help="Description of the provider: same = do not update")

cmd_delprovider = commands.add_parser("dp", help="Delete a host provider")
cmd_delprovider.set_defaults(func="DelProvider")
cmd_delprovider.add_argument("name",
                    nargs=1,
                    action='store',
                    help="Name of the provider")

cmd_addeasylist = commands.add_parser("ae", help="Add a easylist file")
cmd_addeasylist.set_defaults(func="AddEasylist")
cmd_addeasylist.add_argument("list",
                            nargs=1,
                            action="store",
                            help="Name of the list")
cmd_addeasylist.add_argument("url",
                            nargs=1,
                            action="store",
                            help="URL of the easylist file")

cmd_modifyeasylist = commands.add_parser("me", help="Modify a easylist list")
cmd_modifyeasylist.set_defaults(func="ModifyEasylist")
cmd_modifyeasylist.add_argument("list",
                            nargs=1,
                            action="store",
                            help="Name of the list to modify")
cmd_modifyeasylist.add_argument("url",
                            nargs=1,
                            action="store",
                            help="URL of the easylist file: same = do not update")

cmd_deleasylist = commands.add_parser("de", help="Delete a easylist list")
cmd_deleasylist.set_defaults(func="DelEasylist")
cmd_deleasylist.add_argument("list",
                    nargs=1,
                    action='store',
                    help="Name of the list")

cmd_addblackwhite = commands.add_parser("abw", help="Add a domain to the black/white list")
cmd_addblackwhite.set_defaults(func="AddBlackWhite")
cmd_addblackwhite.add_argument("domain",
                            nargs=1,
                            action="store",
                            help="Domain to be added")
cmd_addblackwhite.add_argument("list",
                            nargs=1,
                            choices=['black','white'],
                            action="store",
                            help="Which list to add the domain to. (Black/White)")

cmd_modifyblackwhite = commands.add_parser("mbw", help="Modify a domain in the black/white list")
cmd_modifyblackwhite.set_defaults(func="ModifyBlackWhite")
cmd_modifyblackwhite.add_argument("domain",
                            nargs=1,
                            action="store",
                            help="Domain to modify")
cmd_modifyblackwhite.add_argument("list",
                            nargs=1,
                            action="store",
                            help="Black listed or White listed")

cmd_delblackwhite = commands.add_parser("dbw", help="Delete a black/white listed domain")
cmd_delblackwhite.set_defaults(func="DelBlackWhite")
cmd_delblackwhite.add_argument("domain",
                    nargs=1,
                    action='store',
                    help="Domain to remove")

cmd_hostval = commands.add_parser("hv", help="Validate host domains against DNS")
cmd_hostval.set_defaults(func="HostVal")
cmd_hostval.add_argument("-reset",
                         action="store_true",
                         help="Reset Validation")

cmd_hostval_report = commands.add_parser("hvr", help="Host Validation Report")
cmd_hostval_report.set_defaults(func="HostValReport")

args = parser.parse_args()

DBG = args.verbosity[0]
DB_USER = args.user[0]
DB_HOST = args.host[0]
DB_PASSW = args.password[0]
if config.has_option("SECURITY", "DBNAME"):
    DB_NAME = config.get("SECURITY", "DBNAME")
else:
    DB_NAME = "Hostdb"

debug("Number of arguments: %s\nArguments: %s\nHostDB-Config dir: %s\n" % (len(sys.argv),args,CONFDIR), 3)

if len(sys.argv) < 2:
    parser.print_help()
    sys.exit(0)

# set command to be run on exit
try:
    # Create temporary lock
    touch("%s/%s.lock" % (CONFDIR,TMPNAME))

    cnx = MDB.connect(user=DB_USER,password=DB_PASSW,host=DB_HOST)

    main()

except MDB.Error as err:
    if err.errno == 1044:
        print("Error message:", err.msg)
        sys.exit(err.errno)
    else:
        print("Something went wrong:")
        print("Error code:", err.errno)
        print("SQLSTATE value:", err.sqlstate)
        print("Error message:", err.msg)
        print("Error:", err)
        print(traceback.format_exc())
except:
    print(traceback.format_exc())
finally:
    os.remove("%s/%s.lock" % (CONFDIR,TMPNAME))
    cnx.close()
    sys.exit(0)
