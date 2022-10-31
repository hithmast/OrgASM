import requests
from libs import result_parser as rp
import json
import socket

def hacker_target_parser(domain):
    #get all the subdomain of the domain from hackertarget
    #the url is https://api.hackertarget.com/hostsearch/?q={domain}
    url = "https://api.hackertarget.com/hostsearch/?q=" + domain
    response = requests.get(url)
    """
    the response is in this form :
    fage.fr,81.88.53.29
    jean-marie.fage.fr,185.2.5.85
    anne.fage.fr,185.2.5.85
    benoit.fage.fr,157.90.145.185
    pizza.benoit.fage.fr,157.90.145.185
    content.pizza.benoit.fage.fr,172.104.159.223
    admin.benoit.fage.fr,157.90.145.185
    dolibarr.benoit.fage.fr,82.66.13.124
    content.benoit.fage.fr,157.90.145.185
    """
    #split the response in lines
    lines = response.text.split("\n")
    #get all the subdomains
    subdomains = []
    for line in lines:
        subdomains.append(line.split(",")[0])
    #delete all the occurences in the list
    subdomains = rp.delete_occurences(subdomains)
    return subdomains

def alienvault_parser(domain):
    #get all the subdomain of the domain from alienvault
    #url https://otx.alienvault.com/api/v1/indicators/domain/{domain}/passive_dns
    url = "https://otx.alienvault.com/api/v1/indicators/domain/" + domain + "/passive_dns"
    response = requests.get(url)
    #response is a json format
    #convert response.text in json
    json_data = json.loads(response.text)
    """
    Example of json_data from alienvault
        {
        "passive_dns": [
            {
                "address": "144.76.196.152",
                "first": "2022-10-22T14:19:06",
                "last": "2022-10-22T14:19:06",
                "hostname": "res01.benoit.fage.fr",
                "record_type": "A",
                "indicator_link": "/indicator/hostname/res01.benoit.fage.fr",
                "flag_url": "assets/images/flags/de.png",
                "flag_title": "Germany",
                "asset_type": "hostname",
                "asn": "AS24940 hetzner online gmbh"
            },
            {
                "address": "82.66.13.124",
                "first": "2022-09-24T01:09:12",
                "last": "2022-09-24T01:15:02",
                "hostname": "dolibarr.benoit.fage.fr",
                "record_type": "A",
                "indicator_link": "/indicator/hostname/dolibarr.benoit.fage.fr",
                "flag_url": "assets/images/flags/fr.png",
                "flag_title": "France",
                "asset_type": "hostname",
                "asn": "AS12322 free sas"
            }
    """
    #get all the hostname
    subdomains = []
    for i in json_data["passive_dns"]:
        try :
            subdomains.append(i["hostname"])
        except:
            pass
    #delete all the occurences in the list
    subdomains = rp.delete_occurences(subdomains)
    return subdomains



def from_wordlist(domain):
    #wordlist is Subdomain.txt
    #open the file
    with open("wordlists/subdomains-1000.txt", "r") as file:
        #read all the lines
        lines = file.readlines()
    #test all the subdomains like {subdomain}.{domain}
    subdomains = []
    for line in lines:
        #loaading percentage
        print("Wordlist testing : " + str(round(lines.index(line) / len(lines) * 100, 2)) + "%", end="\r")
        request_to_test = line.strip() + "." + domain
        try:
            #try to connect to the subdomain
            socket.gethostbyname(request_to_test)
            #if the connection is successful, add the subdomain to the list
            subdomains.append(request_to_test)
        except:
            pass
        subdomains = rp.delete_occurences(subdomains)
    return subdomains