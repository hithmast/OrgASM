from libs import dns_request
from libs import sub_harvester as sh
from libs import result_parser as rp
from libs import ip_scan as ips
from libs import custom_logger as cl
from libs import domain_parser as dp
import datetime
import os
import json
import re
from pprint import pprint
import argparse
from jinja2 import Template
import json
import sys
logger = cl.logger


def recursive_subdomains(subs : list, wt :int, wd :str, mode :str, domain :str) -> list:
    temp_subs = []
    new_subs = []
    for subdomain in subs :
        logger.info(f"Recursive scan of {subdomain} | {subs.index(subdomain)}/{len(subs)}")
        if "O" in mode :
            logger.info("Alienvault testing...")
            temp_subs += sh.alienvault_parser(subdomain)
            logger.info("Alienvault testing done")
            logger.info("Hackertarget testing...")
            temp_subs += sh.hacker_target_parser(subdomain)
            logger.info("Hackertarget testing done")
            logger.info("Crt.sh testing...")
            temp_subs += sh.crtsh_parser(subdomain)
            logger.info("Crt.sh testing done")
        if "B" in mode :
            logger.info("Wordlist testing...")
            temp_subs += sh.from_wordlist_thread(subdomain, wt, f"wordlists/{wd}.txt")
            logger.info("Wordlist testing done")
        print("\n") # some space between each subdomain
        temp_subs = rp.delete_occurences(temp_subs)
    for subdomain in temp_subs:
        if subdomain not in subs:
            new_subs.append(subdomain)
    if len(new_subs) == 0:
        return []
    else:
        logger.info(f"Found {len(new_subs)} new subdomains, saved them to : exports/{domain}/dynamic_sub_save.txt")
        rp.dynamic_save(new_subs, domain, "add")
        return new_subs

def menu():
    argpars = argparse.ArgumentParser()
    argpars.add_argument("-d", "--domain", required=False, help="Domain to scan")
    argpars.add_argument("-ip", "--ip", required=False, help="IP to scan")
    argpars.add_argument("-net", "--network", required=False, help="Network to scan, don't forget the CIDR (ex: 192.168.1.0/24)")
    argpars.add_argument("-m", "--mode", required=False, default="OBS", help="Mode to use, O for OSINT (API request), B for bruteforce, S for IP scan (default OBS)")
    argpars.add_argument("-sF", "--subfile", required=False, help="Path to file with subdomains, one per line")
    argpars.add_argument("-ipF", "--ipfile", required=False, help="Path to file with IPs, one per line")
    argpars.add_argument("-R", "--recursive", required=False, default=1, type= int, help="Recursive scan, will rescan all the subdomains finds and go deeper as you want, default is 0")
    argpars.add_argument("-w", "--wordlist", default="medium", type=str, required=False, help="Wordlist to use (small, medium(default), big)")
    argpars.add_argument("-wT", "--wordlistThreads", default=500, type=int, required=False, help="Number of threads to use for Wordlist(default 500)")
    argpars.add_argument("-iS", "--IPScanType", default="W", type=str, required=False, help="Choose what IPs to scan (W: only subdomains IP containing domain given, WR: only subdomains IP containtaining domain given but with a redirect, A: All subdomains detected")
    argpars.add_argument("-iT", "--IPthreads", default=2000, type=int, required=False, help="Number of threads to use for IP scan(default 2000)")
    argpars.add_argument("-sT", "--subdomainsThreads", default=500, type=int, required=False, help="Number of threads to use for check real subdomains(default 500)")
    argpars.add_argument("-cP", "--checkPortsThreads", default=30, type=int, required=False, help="Check all ports of subdomains for all IP in IPScantype (-iS) and try to access them to check if it's a webport (default True) (deactivate with 0)")
    argpars.add_argument("-dT", "--detectTechno", default=True, type=bool, required=False, help="Detect techno used by subdomains (default True) (deactivate with False)")
    argpars.add_argument("-vuln", "--vulnScan", default=False, action="store_true", help="Scan subdomains using Nuclei, you need to have nuclei installed and in your PATH (default False)")
    argpars.add_argument("-vulnconf", "--vulnConfig", default="", type=str, required=False, help="Path to config file for nuclei (default is the default config)")
    argpars.add_argument("-limit", "--limit", default=False, action="store_true", required=False, help="Limit the scope of scan to the domain given or the subdomains given in the file (-sF) (default False)")

    args = argpars.parse_args()
    mode = args.mode
    wordlist_size = args.wordlist
    wordlist_thread_number = int(args.wordlistThreads)
    #verify mode
    if len(mode) > 3 or len(mode) < 1 or not re.match("^[OBS]+$", mode):
        logger.error("Mode not valid, must be O B or S (or concatenation like : OS, OB, OBS)")
        exit(1)
    if mode == "S":
        logger.error("Cannot use only IP scan mode, you have to use at least one of the other modes with it")

    # help for argpars
    domain = ""
    if args.domain:
        domain = args.domain
    
    if args.limit and args.recursive > 0:
        logger.warning("It's recommended to set recursive to 0 when using limit mode")
        input("Do you want to continue ? (y/n) ")
        if input == "n":
            exit(0)
        else :
            pass 
    if args.limit and args.subfile == None:
        logger.warning("It's recommended to put a file with subdomains to scan when using limit mode")
        input("Do you want to continue ? (y/n) ")
        if input == "n":
            exit(0)
        else :
            pass 
    final_dict_result = {}
    #ask for domain name
    #Check if the domain name is valid with regex
    if args.domain:
        while not re.match(r"^[a-zA-Z0-9]+([\-\.]{1}[a-zA-Z0-9]+)*\.[a-zA-Z]{2,5}$", domain):
            logger.error("Invalid domain name")
            domain = input("Enter domain name: ")
        
        if args.subfile:
            all_results=[]
            with open(args.subfile, "r") as file:
                for line in file:
                    all_results.append(line.strip())
        else :
            all_results = []
        
        #get all the subdomains from alienvault
        if "O" in mode :
            logger.info("Alienvault testing...")
            all_results += sh.alienvault_parser(domain)
            logger.info("Alienvault testing done")
            logger.info("Hackertarget testing...")
            all_results += sh.hacker_target_parser(domain)
            logger.info("Hackertarget testing done")
            logger.info("Crt.sh testing...")
            all_results += sh.crtsh_parser(domain)
            logger.info("Crt.sh testing done")
        if "B" in mode :
            logger.info("Wordlist testing...")
            all_results += sh.from_wordlist_thread(domain, args.wordlistThreads, f"wordlists/{wordlist_size}.txt")
            if args.limit and args.subfile != None:
                with open(args.subfile, "r") as file:
                    for line in file:
                        all_results += sh.from_wordlist_thread(line.strip(), args.wordlistThreads, f"wordlists/{wordlist_size}.txt")
            logger.info("Wordlist testing done")

        
        logger.info("Deleting occurences...")
        all_results = rp.delete_occurences(all_results)
        all_results = rp.delete_star(all_results)

        if args.limit:
            sub_file = []
            to_remove = []
            if args.subfile != None:
                with open(args.subfile, "r") as file:
                    for line in file:
                        sub_file.append(line.strip())
                for sub in all_results :
                    if sub not in sub_file and sub != domain:
                        for sub2 in sub_file:
                            if sub2 in sub:
                                continue
                            else :
                                to_remove.append(sub)
                                break
            else :
                for sub in all_results :
                    if sub != domain:
                        to_remove.append(sub)
            for sub in to_remove:
                all_results.remove(sub)
        #clear the screen
        try :
            os.system("cls")
        except:
            # linux
            os.system("clear")
        
        logger.info(f"Actually creating the list of subdomains at : exports/{domain}/dynamic_sub_save.txt")
        rp.dynamic_save(all_results, domain, "create")
        if args.recursive > 0 :
            logger.info("Recursive scan...")
            new_scan = recursive_subdomains(all_results, wordlist_thread_number, wordlist_size, mode, domain)
            all_results += new_scan
            all_results = rp.delete_occurences(all_results)
            counter = 1
            while len(new_scan) > 0 and counter < args.recursive:
                all_results += new_scan
                new_scan = recursive_subdomains(new_scan, wordlist_thread_number, wordlist_size, mode, domain)
                all_results = rp.delete_occurences(all_results)
                counter += 1
            logger.info("Recursive scan done")

        #delete all the occurences in the list
        
        logger.info("Deleting occurences...")
        all_results = rp.delete_occurences(all_results)
        #check subdomains by accessing them with dp.detect_redirect
        if "S" in mode or "B" in mode :
            cl.logger.info("Checking subdomains...")
            subdomains_with_redirect=[]
            temp_all_results = []
            dead_subdomains = []
            temp_all_results, subdomains_with_redirect, dead_subdomains = dp.detect_redirect_with_thread_limit(all_results, args.subdomainsThreads)
            all_results = temp_all_results

            cl.logger.info("Checking subdomains done")
        # for result in all_results:
        #     print("DNS testing : " + str(round(all_results.index(result) / len(all_results) * 100, 2)) + "% ", end="\r")
        #     #dns_request.main return a list
        #     #join all the list in one list
        #     dns_result += dns_request.main(result, args.dnsThreads)
        # all_results+= dns_result
        # logger.info("DNS testing done")
            logger.info("Deleting occurences...")
            all_results = rp.delete_occurences(all_results)
        else :
            subdomains_with_redirect = []
            dead_subdomains = []
        logger.info("All done")
        
        final_dict= rp.result_filter(all_results, domain, subdomains_with_redirect, dead_subdomains)
        logger.info(f"Subdomains containing {domain}:")
        for subdomain in final_dict["subdomain_withdomain"]:
            print(subdomain)
        logger.info(f"Subdomains not containing {domain}:")
        for subdomain in final_dict["subdomain_withoutdomain"]:
            print(subdomain)
        logger.info(f"Subdomains with redirect detected :")
        for subdomain in final_dict["subdomain_with_redirect"]:
            print(subdomain)
        logger.info(f"Dead subdomains :")
        for subdomain in final_dict["dead_subdomains"]:
            print(subdomain)
        final_dict_result = final_dict
        if "S" in mode:
            final_dict_result= {}
            logger.info("IP sorting...")
            ip_dict = ips.get_all_ip(final_dict, domain)
            logger.info("IP sorting done")
            logger.info("IP sorting results:")
            final_dict_result= ip_dict
            #pop dead_subdomains
            final_dict_result["dead_subdomains"] = final_dict["dead_subdomains"]
            pprint(final_dict_result)
            logger.info("Done")
            deads= final_dict_result.pop("dead_subdomains")
            logger.info("IP scanning...")
            if args.IPScanType == "W":
                for ip in final_dict_result :
                    if final_dict_result[ip]["subdomains"]["subdomain_withdomain"] != []:
                        open_ports= ips.port_scan_with_thread_limit(ip, range(65536), args.IPthreads)
                        for port in open_ports:
                            final_dict_result[ip]["ports"][port]= ips.detect_service(ip, port)
            elif args.IPScanType == "WR":
                for ip in final_dict_result :
                    if final_dict_result[ip]["subdomains"]["subdomain_with_redirect"] != [] or final_dict_result[ip]["subdomains"]["subdomain_withdomain"] != []:
                        open_ports= ips.port_scan_with_thread_limit(ip, range(65536), args.IPthreads)
                        for port in open_ports:
                            final_dict_result[ip]["ports"][port]= ips.detect_service(ip, port)
            elif args.IPScanType == "A":
                for ip in final_dict_result :
                    open_ports= ips.port_scan_with_thread_limit(ip, range(65536), args.IPthreads)
                    for port in open_ports:
                        final_dict_result[ip]["ports"][port]= ips.detect_service(ip, port)


            logger.info("IP scanning done")
            logger.info("IP scanning service analysis...")
            final_dict_result= rp.service_recognizer(final_dict_result)
            logger.info("IP scanning service analysis done")
            logger.info("Detecting web ports...")
            if args.checkPortsThreads != 0:
                final_dict_result= dp.detect_web_port(final_dict_result, args.checkPortsThreads, args.IPScanType)
            if args.detectTechno :
                final_dict_result = dp.detect_web_techno(final_dict_result, args.IPScanType)
                final_dict_result = dp.detect_web_techno_domain(final_dict_result, args.IPScanType)
            if args.vulnScan :
                final_dict_result = ips.run_parse_nuclei(final_dict_result, domain, args.IPScanType, args.vulnConfig)
            logger.info("Detecting web ports done")
            logger.info("IP scanning results:")
            final_dict_result["dead_subdomains"]= deads
            pprint(final_dict_result)
            logger.info("Done")

    elif args.ip :
        if args.ipfile :
            logger.error("You can't use -ip and -ipFile at the same time")
            exit(1)
        if args.network :
            logger.error("You can't use -ip and -network at the same time")
            exit(1)
        final_dict_result= {
            args.ip : {
                "ports" : {},
                "subdomains" : {
                    "subdomain_withdomain" : [],
                    "subdomain_withoutdomain" : [],
                    "subdomain_with_redirect" : [],
                    "dead_subdomains" : [],
                    "vulns" : {},
                },
                "techno" : {
                    "web" : [],
                    "web_domain" : []
                },
                "vulns" : []
            }
        }
        logger.info("IP scanning...")
        open_ports= ips.port_scan_with_thread_limit(args.ip, range(65536), args.IPthreads)
        for port in open_ports:
            final_dict_result[args.ip]["ports"][port]= ips.detect_service(args.ip, port)
        logger.info("IP scanning done")
        logger.info("IP scanning service analysis...")
        final_dict_result= rp.service_recognizer(final_dict_result)
        logger.info("IP scanning service analysis done")
        logger.info("Detecting web ports...")
        if args.checkPortsThreads != 0:
            final_dict_result= dp.detect_web_port(final_dict_result, args.checkPortsThreads, "A")
        if args.detectTechno :
            final_dict_result = dp.detect_web_techno(final_dict_result, "A")
            final_dict_result = dp.detect_web_techno_domain(final_dict_result, "A")
        if args.vulnScan :
            logger.info('Running nuclei scan...')
            final_dict_result = ips.run_parse_nuclei(final_dict_result, domain, "A", args.vulnConfig)
        logger.info("Detecting web ports done")
        logger.info("IP scanning results:")
        pprint(final_dict_result)
        logger.info("Done")

    elif args.ipfile :
        if args.network :
            logger.error("You can't use -ipFile and -network at the same time")
            exit(1)
        if args.ip :
            logger.error("You can't use -ipFile and -ip at the same time")
            exit(1)
        final_dict_result= {}
        logger.info("IP scanning...")
        with open(args.ipfile, "r") as file:
            for line in file:
                ip= line.strip()
                final_dict_result[ip] = {
                    "ports" : {},
                    "subdomains" : {
                        "subdomain_withdomain" : [],
                        "subdomain_withoutdomain" : [],
                        "subdomain_with_redirect" : [],
                        "dead_subdomains" : [],
                        "vulns" : {},
                    },
                    "techno" : {
                        "web" : [],
                        "web_domain" : []
                    },
                    "vulns" : []
                }
                open_ports= ips.port_scan_with_thread_limit(ip, range(65536), args.IPthreads)
                for port in open_ports:
                    final_dict_result[ip]["ports"][port]= ips.detect_service(ip, port)
        logger.info("IP scanning done")
        logger.info("IP scanning service analysis...")
        final_dict_result= rp.service_recognizer(final_dict_result)
        logger.info("IP scanning service analysis done")
        logger.info("Detecting web ports...")
        if args.checkPortsThreads != 0:
            final_dict_result= dp.detect_web_port(final_dict_result, args.checkPortsThreads, "A")
        if args.detectTechno :
            final_dict_result = dp.detect_web_techno(final_dict_result, "A")
            final_dict_result = dp.detect_web_techno_domain(final_dict_result, "A")
        if args.vulnScan :
            logger.info('Running nuclei scan...')
            final_dict_result = ips.run_parse_nuclei(final_dict_result, domain, "A", args.vulnConfig)
        logger.info("Detecting web ports done")
        logger.info("IP scanning results:")
        pprint(final_dict_result)
        logger.info("Done")

    elif args.network :
        if args.ipfile :
            logger.error("You can't use -network and -ipFile at the same time")
            exit(1)
        if args.ip :
            logger.error("You can't use -network and -ip at the same time")
            exit(1)
        final_dict_result= {}
        logger.info("Network scanning...")
        for ip in ips.get_ip_from_network(args.network):
            ip = ip["ip"]
            final_dict_result[ip] = {
                "ports" : {},
                "subdomains" : {
                    "subdomain_withdomain" : [],
                    "subdomain_withoutdomain" : [],
                    "subdomain_with_redirect" : [],
                    "dead_subdomains" : [],
                    "vulns" : {},
                },
                "techno" : {
                    "web" : [],
                    "web_domain" : []
                },
                "vulns" : []
            }
            open_ports= ips.port_scan_with_thread_limit(ip, range(65536), args.IPthreads)
            for port in open_ports:
                final_dict_result[ip]["ports"][port]= ips.detect_service(ip, port)
        logger.info("IP scanning done")
        logger.info("IP scanning service analysis...")
        final_dict_result= rp.service_recognizer(final_dict_result)
        logger.info("IP scanning service analysis done")
        logger.info("Detecting web ports...")
        if args.checkPortsThreads != 0:
            final_dict_result= dp.detect_web_port(final_dict_result, args.checkPortsThreads, "A")
        if args.detectTechno :
            final_dict_result = dp.detect_web_techno(final_dict_result, "A")
            final_dict_result = dp.detect_web_techno_domain(final_dict_result, "A")
        if args.vulnScan :
            logger.info('Running nuclei scan...')
            final_dict_result = ips.run_parse_nuclei(final_dict_result, domain, "A", args.vulnConfig)
        logger.info("Detecting web ports done")
        logger.info("IP scanning results:")
        pprint(final_dict_result)
        logger.info("Done")


    if not os.path.exists("exports"):
        os.mkdir("exports")

    date = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    file_name = f"result_{domain.replace('.','-')}_{date}.json"
    with open("exports/"+domain+"/"+file_name, "w") as f:
        json.dump(final_dict_result, f, indent=4)
    logger.info(f"File saved in exports/{file_name}")

    template = Template(open("website/jinja_template.html").read(), autoescape=True)
    html = template.render(data=final_dict_result, metadata={"version": "1.0.0"})
    with open(f"exports/{domain}/html_report_{domain}_{date}.html", "w") as file:
        file.write(html)
    logger.info(f"HTML report saved in exports/{domain}/html_report_{domain}_{date}.html")
    input("Press enter to open the result in your browser...")
    path = os.sep.join([os.getcwd(),f"exports/{domain}/html_report_{domain}_{date}.html"])
    if os.name == "nt":
        os.startfile(path)
    if sys.platform.startswith("linux"):
        os.system("xdg-open " + path)
    logger.info("Exiting...")

if __name__ == "__main__":
    menu()

