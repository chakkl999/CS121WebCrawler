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

def sortDomain(domain: dict):
    if not domain:
        return {}
    for key, value in domain.items():
        domain[key][1] = sortDomain(value[1])
    return dict(sorted(domain.items()))

def outputSubDomain(domain: dict, f = None):
    if not f:
        for key, value in domain.items():
            print(f"{key}, {value[0]}")
    else:
        for key, value in domain.items():
            f.write(f"{key}, {value[0]}\n")

def isnum(text: str):
    return any(i.isnumeric() for i in text)

def outputResult():
    print("Calculating result...")
    domain = {"ics.uci.edu": [1, {}], "cs.uci.edu": [1, {}], "informatics.uci.edu": [1, {}], "stat.uci.edu": [1, {}],
              "today.uci.edu/department/information_computer_sciences": [1, {}]}
    commonWords = {}
    maxNumWords = 0
    longestPage = ""
    for file in pathlib.Path("output").glob("*.txt"):
        with open(file, "r") as f:
            try:
                data = json.load(f)
            except json.decoder.JSONDecodeError:
                pass
            else:
                if data.get("unique", 1) == 1:
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
                        maxNumWords = currentNumWords
    print("...")
    domain = sortDomain(domain)
    print("...")
    unique = countUniquePages(domain)
    limit = 1
    stopWords = {"a", "about", "above", "after", "against", "again", "all", "am", "an", "and", "any", "are", "aren't",
                 "t", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
                 "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't",
                 "down", "during", "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have",
                 "haven't", "having", "he'd", "he'll", "he's", "d", "ll", "s", "her", "here", "here's", "hers",
                 "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "m", "ve", "if",
                 "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's", "me", "more", "most", "more",
                 "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "once", "only", "or", "other", "ought",
                 "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's",
                 "should", "shouldn't", "so", "some", "such", "than", "that", "that's", "the", "their", "theirs", "them",
                 "themselves", "then", "there", "there's", "these", "they", "they'd", "they'll", "they're", "they've",
                 "this", "those", "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we", "we'd",
                 "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when", "when's", "where", "where's",
                 "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you",
                 "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves", "img", "btn", "div",
                 "px", "www", "com", "edu", "pdf", "org", "http"}
    with open("output/result.txt", "w") as f:
        f.write(f"There are {unique} unique pages found.\n")
        f.write(f"Longest page: {longestPage} -> {maxNumWords} words.\n")
        f.write("Common words:\n")
        print(f"There are {unique} unique pages found.")
        print(f"Longest page: {longestPage} -> {maxNumWords} words.")
        print("Common words: ")
        for word in sorted(commonWords.items(), key=lambda f: (-f[1], f[0]), reverse=True)[::-1]:
            if len(word[0]) > 2 and not isnum(word[0]) and word[0] not in stopWords:
                print(f"{limit}. {word[0]} -> {word[1]}")
                f.write(f"{limit}. {word[0]} -> {word[1]}\n")
                limit += 1
            if limit > 50:
                break
        f.write(f"Domain: ics.uci.edu has {domain['ics.uci.edu'][0]} unique page(s).\n")
        f.write("Subdomain: \n")
        print(f"Domain: ics.uci.edu has {domain['ics.uci.edu'][0]} unique page(s).")
        print("Subdomain: ")
        outputSubDomain(domain['ics.uci.edu'][1])
        outputSubDomain(domain['ics.uci.edu'][1], f)
    print(domain)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--restart", action="store_true", default=False)
    parser.add_argument("--config_file", type=str, default="config.ini")
    args = parser.parse_args()
    main(args.config_file, args.restart)
    outputResult()