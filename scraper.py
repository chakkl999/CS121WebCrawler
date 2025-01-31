import re
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
import hashlib
from bs4 import BeautifulSoup, Comment, Doctype
import requests
import json
import pathlib
import time
from utils import get_logger
from utils.response import Response
import cbor

fingerPrints = {}
for file in pathlib.Path("output").glob("*.txt"):
    with open(file, 'r') as f:
        try:
            data = json.load(f)
        except json.decoder.JSONDecodeError:
            pass
        else:
            fingerPrints[data["id"]] = data["fingerPrint"]
robottxt = {}
logger = get_logger(f"Scraper: ", "Scraper")

def scraper(url, resp):
    global fingerPrints, logger
    if resp.status != requests.codes.ok:
        if resp.status >= 600:
            logger.info(f"{url} returned a status code {resp.status}")
        return []
    if url not in fingerPrints:
        soup = BeautifulSoup(resp.raw_response.content, "html.parser")
        links = extract_next_links(url, soup)
        text = []
        cleanSoup(soup)
        for t in soup.find_all(text=True):
            if not isinstance(t, Comment) and not isinstance(t, Doctype) and removejunk(t):
                text.extend(tokenize(t))
        data = {}
        data["unique"] = 1
        data["id"] = url
        data["freq"] = computeWordFrequencies(text)
        data["fingerPrint"] = createFingerPrint(data["freq"])
        if not data["freq"]:
            logger.info(f"{url} is empty, data will kept but will not be counted.")
            fingerPrints[url] = data["fingerPrint"]
            fingerPrints["unique"] = 0
            dumpdata(data)
            return []
        for u, fp in fingerPrints.items():
            percent = compareFingerPrint(data["fingerPrint"], fp)
            if(percent > 90):
                logger.info(f"{url} has similar content to other page(s), data will be kept but will not be counted.")
                fingerPrints[url] = data["fingerPrint"]
                fingerPrints["unique"] = 0
                dumpdata(data)
                return []
        fingerPrints[url] = data["fingerPrint"]
    else:
        logger.info(f"{url} has already been scrapped.")
        return []
    dumpdata(data)
    return [link for link in links if is_valid(link)]

def extract_next_links(url, soup):
    # Implementation requred.
    links = []
    parsedurl = urlparse(url)
    baseurl = parsedurl.scheme + "://" + parsedurl.netloc
    for link in soup.find_all('a'):
        temp = link.get("href")
        try:
            if re.match("//.+", temp):
                temp = ("https:" + temp)
            elif re.match("/.+", temp):
                temp = (baseurl+temp)
            temp = re.sub("#.*", "", temp)
            temp = re.sub("(\?replytocom=.*|\?share=.*|\?n=https.*|\?1=.*|\?c=https.*|\?do=diff.*|\?rev=.*|\?action=login.*|\?action=edit.*|\?action=refcount.*|\?action=source.*|\?action=diff.*|\?action=download.*)", "", temp)
            if temp not in links:
                links.append(temp)
        except:
            pass
    return links

def is_valid(url):
    global robottxt, logger
    if not url:
        return False
    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False
        if re.match("(((.+\.|/)(ics.uci.edu|cs.uci.edu|informatics.uci.edu|stat.uci.edu|today.uci.edu/department/information_computer_sciences))|(ics.uci.edu|cs.uci.edu|informatics.uci.edu|stat.uci.edu|today.uci.edu/department/information_computer_sciences))$",parsed.netloc):
            robot = robottxt.get(parsed.netloc, None)
            if not robot:
                time.sleep(0.5)
                robot = RobotFileParser(parsed.scheme + "://" + parsed.netloc + "/robots.txt")
                try:
                    robot.read()
                except:
                    pass
                robottxt[parsed.netloc] = robot
            if robot.can_fetch("IR F19 63226723", url):
                if re.match(
                        r".*\.(css|js|bmp|gif|jpe?g|ico"
                        + r"|png|tiff?|mid|mp2|mp3|mp4"
                        + r"|wav|avi|mov|mpe?g|ram|m4v|mkv|ogg|ogv|pdf"
                        + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
                        + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
                        + r"|epub|dll|cnf|tgz|sha1|sql"
                        + r"|thmx|mso|arff|rtf|jar|csv"
                        + r"|rm|smil|wmv|swf|wma|zip|rar|gz|ipynb|war|ps.z|eps.z|h|java|py|ppsx)$", parsed.path.lower()):
                    logger.info(f"{url} is not valid.")
                    return False
                if re.match(
                        r".*\.(css|js|bmp|gif|jpe?g|ico"
                        + r"|png|tiff?|mid|mp2|mp3|mp4"
                        + r"|wav|avi|mov|mpe?g|ram|m4v|mkv|ogg|ogv|pdf"
                        + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
                        + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
                        + r"|epub|dll|cnf|tgz|sha1|sql"
                        + r"|thmx|mso|arff|rtf|jar|csv"
                        + r"|rm|smil|wmv|swf|wma|zip|rar|gz|ipynb|war|ps.z|eps.z|h|java|py|ppsx|m|mat)$", parsed.query.lower()):
                    logger.info(f"{url} is not valid.")
                    return False
                if re.match(
                        r".*/(css|js|bmp|gif|jpe?g|ico"
                        + r"|png|tiff?|mid|mp2|mp3|mp4"
                        + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
                        + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
                        + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
                        + r"|epub|dll|cnf|tgz|sha1|raw-attachment|zip-attachment|attachment"
                        + r"|thmx|mso|arff|rtf|jar|csv|~eppstein/pix|uploads|video|pub"
                        + r"|rm|smil|wmv|swf|wma|zip|rar|gz|ipynb)/", parsed.path.lower()):
                    logger.info(f"{url} is not valid.")
                    return False
                return True
            logger.info(f"{url} cannot be scrape according to robots.txt")
        return False
    except TypeError:
        print("TypeError for ", parsed)
        raise
    except:
        pass
    return False

def createFingerPrint(frequency):
    size = 128
    v = [0] * size
    for key, value in frequency.items():
        hash = int(hashlib.md5(key.encode("utf-8")).hexdigest(), 16)
        for i in range(size):
            if((hash & (1 << (size-1-i))) != 0):
                v[i] += value
            else:
                v[i] -= value
    fingerprint = 0
    for i in range(size):
        if(v[i] > 0):
            fingerprint = (fingerprint | (1 << (size-1-i)))
    return fingerprint

def compareFingerPrint(f1, f2):
    if f2 == 0:
        return 0
    similarity = bin(f1 ^ f2)[2:]
    return int(similarity.count('0') / 128 * 100)

def computeWordFrequencies(tokens: list) -> dict:
    freq = {}
    for token in tokens:
        if token in freq:
            freq[token] += 1
        else:
            freq[token] = 1
    toRemove = []
    for key, value in freq.items():
        if len(key) > 2 and key.endswith("s"):
            if key[:len(key)-1] in freq:
                freq[key[:len(key)-1]] += value
                toRemove.append(key)
        if len(key) > 3 and key.endswith("es"):
            if key[:len(key)-2] in freq:
                freq[key[:len(key)-2]] += value
                toRemove.append(key)
    for r in toRemove:
        freq.pop(r, None)
    freq = dict(sorted(freq.items(), key = lambda f: (-f[1], f[0])))
    return freq

def tokenize(text: str):
    leading = re.compile("^[^a-zA-Z0-9]*")
    trailing = re.compile("[^a-zA-Z0-9]*$")
    splitting = re.compile("[^a-zA-Z0-9']")
    tokens = list(filter(None, splitting.split(leading.sub("", trailing.sub("", text.lower())))))
    return [t.strip("'") for t in tokens]

def removejunk(text: str):
    if(text.strip() == ''):
        return False
    if re.match('["a-zA-Z0-9]*:["a-zA-Z0-9]*', text):
        return False
    if re.match("<.*>|\[.*\]|\{.*\}", text):
        return False
    return True

def dumpdata(data):
    urlindex = hashlib.md5(data["id"].encode()).hexdigest()
    pathlib.Path("output").mkdir(parents=True, exist_ok=True)
    pathlib.Path("output/"+urlindex+".txt").touch(exist_ok=True)
    with open("output/"+urlindex+".txt", "w") as f:
        json.dump(data, f)

def cleanSoup(soup):
    for s in soup.find_all("script"):
        s.decompose()
    for sidebar in soup.find_all("div", class_="grid_4 omega sidebar"):
        sidebar.decompose()
    for fragment in soup.find_all("a", href="#"):
        fragment.decompose()
    for f in soup.find_all("footer"):
        f.decompose()
    for login in soup.find_all(attrs={"id": (re.compile("login"), re.compile("fancybox"))}):
        login.decompose()