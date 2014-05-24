#!/usr/bin/env python
#
######################################################################
#
#                  Author: Raymond Jay Bullock
#                  Version: 0.7
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
#                   Validate Domains against DNS
#                   Incorporate Adblock easylist conversion
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
from subprocess import PIPE, Popen
from tempfile import NamedTemporaryFile
import mysql.connector as MDB
from mysql.connector import errorcode
from prettytable import from_db_cursor
import datetime

######################################################################
#
#                  script variables
#
######################################################################

CONFDIR="c:\privoxy"
TMPNAME=os.path.splitext(os.path.basename(__file__))[0]
BYPASSPROXY = True

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
    
    add_domain = """
        INSERT INTO tblBlackWhite (Domain, List)
        VALUES (%(Domain)s, %(List)s)
        """
    select_domain = """
        SELECT COUNT(*) FROM tblBlackWhite
        WHERE ((Domain = %(Domain)s))
        """

    select_list = """
        SELECT List FROM tblBlackWhite
        WHERE ((Domain = %(Domain)s))
        """

    debug("DATA: %s\n" % provider, 3)
    debug(".. Adding %s to HostDB\n" % provider["name"], 0)
    debug(".... Domain: %s\n.... List: %s\n" % (blackwhite["domain"],blackwhite["list"]), 2)
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

def ListProviders():
    cnx.database = DB_NAME
    cursor = cnx.cursor()

    debug(".. List of Providers\n", 0)

    cursor.execute("SELECT Provider, URL, Description, LastModified, ETag FROM tblProvider")
    
    ptable = from_db_cursor(cursor)
    ptable.align["Provider"] = "l"
    ptable.align["URL"] = "l"
    ptable.align["Description"] = "l"
    ptable.align["LastModified"] = "l"
    ptable.align["Etag"] = "l"
    print(ptable)
    cursor.close()
    
def ListBlackWhite():
    cnx.database = DB_NAME
    cursor = cnx.cursor()

    debug(".. List of Black/White domains\n", 0)

    cursor.execute("SELECT Domain, List FROM tblBlackWhite")
    
    ptable = from_db_cursor(cursor)
    ptable.align["Domain"] = "l"
    ptable.align["List"] = "l"
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
        buf = read_f(buf_size)

    f.close()
    
    return lines

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

# progress bar
def drawProgressBar(percent, barLen = 20):
    if isinstance(percent, int):
        percent = float(percent)
    progress = ""
    block = int(round(barLen*percent))
    if block >= 1 and block < barLen:
        block -= 1
        progress = "="*block + ">" + " "*(barLen-block-1)
    else:
        progress = "="*block + " "*(barLen-block)

    sys.stdout.write("\r[{0}] {1}%".format(progress, int(round(percent * 100))))
    sys.stdout.flush()

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
    del_domain = """
        DELETE domain
        FROM tblDomain AS domain
        LEFT OUTER JOIN tblHost AS host
            ON host.IDDomain = domain.IDDomain
        WHERE host.IDDomain IS NULL
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
            if file_size: drawProgressBar(float(file_size_dl / file_size), 50)
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
            drawProgressBar(float(host_size_p / host_size), 50)
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
                'IDDomain': hostcurs.lastrowid,
            }
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

    debug("DATA: %s\n" % hosttype, 3)
    debug(".. Creating Hosts File Started ...\n", 0)

    # hosts: ipaddr domain
    if hosttype['type'] == 'host':
        host_file = open("%s/HOSTS" % CONFDIR, "w")
        debug(".... Creating: %s/HOSTS ...\n" % CONFDIR, 2)
        
        host_file.write("# Generated by HostDB\n# Generated on %s\n" % datetime.date.today())
        cursor.execute(host_select_domain)
        for domain in cursor.fetchall():
            host_file.write("%s %s\n" % (hosttype['ipaddr'], domain[0]))

        debug(".... Creating HOSTS completed\n", 2)
        host_file.close()

    # dnsmasq: "address=/domain/ipaddr
    if hosttype['type'] == 'dnsmasq':
        host_file = open("%s/dnsmasq.custom" % CONFDIR, "w")
        debug(".... Creating: %s/dnsmasq.custom ...\n" % CONFDIR, 2)
        
        host_file.write("# Generated by HostDB\n# Generated on %s\n" % datetime.date.today())
        cursor.execute(host_select_domain)
        for domain in cursor.fetchall():
            host_file.write("address=/%s/%s\n" % (domain[0], hosttype['ipaddr']))

        debug(".... Creating dnsmasq.custom completed\n", 2)
        host_file.close()

    # privoxy: header -> domains
    #Header: { +block{HostDB} +handle-as-image }
    if hosttype['type'] == 'privoxy':
        host_file = open("%s/hostdb.action" % CONFDIR, "w")
        debug(".... Creating %s/hostdb.action ...\n" % CONFDIR, 2)

        host_file.write("# Generated by HostDB\n# Generated on %s\n" % datetime.date.today())
        host_file.write("{ +block{HostDB} +handle-as-image }\n")
        cursor.execute(host_select_domain)
        for domain in cursor.fetchall():
            host_file.write("%s\n" % domain[0])

        debug(".... Creating hostdb.action completed\n", 2)
        host_file.close()

    debug(".. Creating Hosts File Completed\n", 0)
    cursor.close()

def main():
    debug("HostDB starting...\n\n", 0)

    # build command without optionals
    options = {i:str(vars(args)[i]).strip("[]'") for i in vars(args) if i in
               ["name", "url", "description", "type", "ipaddr", "domain", "list"]}
    debug("Options: %s Len: %s\n" % (options, len(options)), 3)

    if len(options) > 0:
        globals()[args.func](options)
    else:
        globals()[args.func]()
    
    debug("\nHostDB completed\n", 0)

# check whether an instance is already running
if os.path.isfile("%s/%s.lock" % (CONFDIR,TMPNAME)):
    print("An Instance of {0} is already running. Exit".format(TMPNAME))
    sys.exit(1)

parser = argparse.ArgumentParser(prog='HostDB',description='Manager tool for hosts file(s)',
                                 formatter_class=argparse.RawTextHelpFormatter)

# Optional options
parser.add_argument("-v", metavar="#",
                    nargs=1,
                    default=[0],
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
                    version='%(prog)s v0.6')

# Optional Connection Specific options
secure = parser.add_argument_group('Connection', 'Optional connection information')
secure.add_argument("-u",
                    nargs=1,
                    default=["python"],
                    help="Set the user to use",
                    action="store", dest="user")
secure.add_argument("-p",
                    nargs=1,
                    default=[""],
                    help="Set the password to use",
                    action="store", dest="password")
secure.add_argument("-ho",
                    nargs=1,
                    default=["127.0.0.1"],
                    help="Set the host to use",
                    action="store", dest="host")

# Command Options, only one can be used
commands = parser.add_subparsers(title="Command",
                                 description="valid commands",
                                 help="additional help and exit")

cmd_downloadhost = commands.add_parser("dh", help="Dowload the host files from the providers if it has been updated.")
cmd_downloadhost.set_defaults(func="DownloadHostFiles")

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

cmd_addblackwhite = commands.add_parser("abw", help="Add a domain to the black/white list")
cmd_addblackwhite.set_defaults(func="AddBlackWhite")
cmd_addblackwhite.add_argument("domain",
                            nargs=1,
                            action="store",
                            help="Domain to be added")
cmd_addblackwhite.add_argument("list",
                            nargs=1,
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

args = parser.parse_args()

DBG = args.verbosity[0]
DB_USER = args.user[0]
DB_HOST = args.host[0]
DB_PASSW = args.password[0]
DB_NAME = "Hostdb"

debug("Number of arguments: %s\nArguments: %s\nHostVal-Config dir: %s\n" % (len(sys.argv),args,CONFDIR), 3)

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
