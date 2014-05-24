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

usage: HostDB [-h] [-v #] [-ver] [-u USER] [-p PASSWORD] [-ho HOST]
              {dh,ch,lbw,lp,setup,ap,mp,dp,abw,mbw,dbw} ...

Manager tool for hosts file(s)

optional arguments:
  -h, --help            show this help message and exit
  -v #                  Set level of messages, where
                            0: Normal Output
                            1: A little more information
                            2: All information
                            3: Developer use for displaying debug information
  -ver, --version       show program's version number and exit

Connection:
  Optional connection information

  -u USER               Set the user to use
  -p PASSWORD           Set the password to use
  -ho HOST              Set the host to use

Command:
  valid commands

  {dh,ch,lbw,lp,setup,ap,mp,dp,abw,mbw,dbw}
                        additional help and exit
    dh                  Dowload the host files from the providers if it has been updated.
    ch                  Create a host file
    lbw                 List current black/white listed domains
    lp                  List all current providers
    setup               Setup hostdb database
    ap                  Add a provider of host list
    mp                  Modify a provider of host list
    dp                  Delete a host provider
    abw                 Add a domain to the black/white list
    mbw                 Modify a domain in the black/white list
    dbw                 Delete a black/white listed domain
	
Command ch [-ipaddr IPADDR] {host,dnsmasq,privoxy}

positional arguments:
  {host,dnsmasq,privoxy}
                        Type of host file to create. Where:
                           host: Create a standard windows type host

optional arguments:
  -ipaddr IPADDR        What IP Address to use in the host file redirection
                           Default: 127.0.0.1
						   
Command ap name url description

positional arguments:
  name         Name of the provider
  url          URL of the provider's host file
  description  Description of the provider

Command mp name url description

positional arguments:
  name         Name of the provider to modify
  url          URL of the provider's host file: same = do not update
  description  Description of the provider: same = do not update
  
Command dp name domain 
                                  
positional arguments:             
  name        Name of the provider

Command abw domain list

positional arguments:
  domain      Domain to be added
  list        Which list to add the domain to. (Black/White)

Command mbw domain list

positional arguments:
  domain      Domain to modify
  list        Black listed or White listed

Command dbw domain

positional arguments:
  domain      Domain to remove
