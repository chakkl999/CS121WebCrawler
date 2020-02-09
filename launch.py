from configparser import ConfigParser
from argparse import ArgumentParser

from utils.server_registration import get_cache_server
from utils.config import Config
from crawler import Crawler
import re
import pathlib
import json
from urllib.parse import urlparse

def main(config_file, restart):
    cparser = ConfigParser()
    cparser.read(config_file)
    config = Config(cparser)
    config.cache_server = get_cache_server(config, restart)
    crawler = Crawler(config, restart)
    crawler.start()

def countDomain(domain: dict, url):
    for d in domain.keys():
        if(re.match(d+"$", url)): #exact match, same domain, count it as a unique page
            domain[d][0] += 1
            return
        elif(re.match(".+\."+d+"$", url)): #near match, subdomain, need to check the subdomain also
            return countDomain(domain[d][1], url)
    domain[url] = [1, {}] #if it doesn't match with any domain, it means it's a new domain, add it to the dict
    return

def countUniquePages(domain: dict):
    unique = 0
    for value in domain.values():
        unique += value[0]
        for subvalue in value[1].values():
            unique += subvalue[0]
    return unique

# def countDomain(domain: dict, url):
#     for d in domain.keys():
#         if re.match(d, url):
#             domain[d][0] += 1
#             return
#         elif re.match(".+\." + d + "$", url):
#             if url in domain[d][1]:
#                 domain[d][1][url][0] += 1
#             else:
#                 domain[d][1][url] = [1, {}]
#             return
#     domain[url] = [1, {}] #if it doesn't match with any domain, it means it's a new domain, add it to the dict, shouldn't happen but ill put it here

def sortDomain(domain: dict):
    if not domain:
        return {}
    for key, value in domain.items():
        domain[key][1] = sortDomain(value[1])
    return dict(sorted(domain.items()))

def outputSubDomain(domain: dict):
    for key, value in domain:
        print(f"{key}, {value[0]}")

def outputResult():
    domain = {"ics.uci.edu": [1, {}], "cs.uci.edu": [1, {}], "informatics.uci.edu": [1, {}], "stat.uci.edu": [1, {}],
              "today.uci.edu/department/information_computer_sciences": [1, {}]}
    commonWords = {}
    maxNumWords = 0
    longestPage = ""
    for file in pathlib.Path("output").glob("*.txt"):
        with open(file, "r") as f:
            data = json.load(f)
            if data["unique"] == 1:
                url = re.sub("^www.", "", urlparse(data["id"]).netloc)
                countDomain(domain, url)
                currentNumWords = 0
                for key, value in data["freq"].items():
                    currentNumWords += value
                    if key in commonWords:
                        commonWords[key] += value
                    else:
                        commonWords[key] = value
                if currentNumWords > maxNumWords:
                    longestPage = data["id"]
    domain = sortDomain(domain)
    unique = countUniquePages(domain)
    print(f"There are {unique} unique pages found.")
    print(f"Longest page: {longestPage} -> {maxNumWords} words.")
    limit = 0
    print("Common words: ")
    stopWords = {}
    for word in sorted(commonWords.items(), key=lambda f: (-f[1], f[0]), reverse=True)[::-1]:
        if word[0] not in stopWords and not word[0].isnumeric():
            print(f"{word[0]} -> {word[1]}")
            limit += 1
        if limit > 50:
            break
    print(f"Domain: ics.uci.edu has {domain['ics.uci.edu'][0]} unique page(s).")
    print("Subdomain: ")
    outputSubDomain(domain['ics.uci.edu'][1])

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--restart", action="store_true", default=False)
    parser.add_argument("--config_file", type=str, default="config.ini")
    args = parser.parse_args()
    main(args.config_file, args.restart)
    outputResult()