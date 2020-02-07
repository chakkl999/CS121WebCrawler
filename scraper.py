import re
from urllib.parse import urlparse
import hashlib
from bs4 import BeautifulSoup, Comment, Doctype
import requests
import json
import pathlib

global fingerPrints
fingerPrints = {}

def scraper(url, resp):
    if resp.status_code != requests.codes.ok:
        print(f"{url} returns an status code {resp.status_code}")
        return []
    global fingerPrints
    links = extract_next_links(url, resp)
    soup = BeautifulSoup(resp.text)
    text = []
    for s in soup.find_all("script"):
        s.decompose()
    for t in soup.find_all(text=True):
        if not isinstance(t, Comment) and not isinstance(t, Doctype) and removejunk(t):
            text.extend(tokenize(t))
    data = {}
    data["freq"] = computeWordFrequencies(text)
    data["fingerPrint"] = createFingerPrint(data["freq"])
    if url not in fingerPrints:
        for u, fp in fingerPrints.items():
            percent = compareFingerPrint(data["fingerPrint"], fp)
            if(percent > 80):
                print(f"{url} has the same content to other page(s), ignoring this page.")
                fingerPrints[url] = data["fingerPrint"]
                return []
        fingerPrints[url] = data["fingerPrint"]
    else:
        print(f"{url} has the same content to other page(s), ignoring this page.")
        return []
    dumpdata(url, data)
    return [link for link in links if is_valid(link)]

def extract_next_links(url, resp):
    # Implementation requred.
    soup = BeautifulSoup(resp.text)
    links = []
    baseurl = re.match("(https?://.*?)/", url)
    for link in soup.find_all('a'):
        temp = link.get("href")
        if temp not in links:
            if re.match("//.+", temp):
                links.add("https:" + temp)
            elif re.match("/.+", temp):
                links.add(baseurl+temp)
    return links

def is_valid(url):
    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False
        if not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower()):
            return True
    except TypeError:
        print ("TypeError for ", parsed)
        raise
    return False

def createFingerPrint(frequency):
    size = 128
    v = [0] * size
    for key, value in frequency.items():
        hash = int(hashlib.md5(key.encode("utf-8")).hexdigest(), 16)
        for i in range(size-1, -1, -1):
            if((hash & (1 << i)) != 0):
                v[i] += value
            else:
                v[i] -= value
    fingerprint = 0
    for i in range(size):
        if(v[i] > 0):
            fingerprint = (fingerprint | (1 << i))
    return fingerprint

def compareFingerPrint(f1, f2):
    similarity = bin(f1 ^ f2)[2:]
    num = 0
    for bit in similarity:
        if bit == '0':
            num += 1
    return int(num/128 * 100)

def computeWordFrequencies(tokens: list) -> dict:
    freq = {}
    for token in tokens:
        token = token.capitalize();
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
    freq = sorted(freq.items(), key=lambda f: (-f[1], f[0]), reverse=True)[::-1]
    return freq

def tokenize(text):
    leading = re.compile("^[^a-zA-Z0-9]*")
    trailing = re.compile("[^a-zA-Z0-9]*$")
    spliting = re.compile("[^a-zA-Z0-9]")
    return list(filter(None, spliting.split(leading.sub("", trailing.sub("", text)))))

def removejunk(text: str):
    if(text.strip() == ''):
        return False
    if re.match('["a-zA-Z0-9]*:["a-zA-Z0-9]*', text):
        return False
    if re.match("<.*>|\[.*\]|{.*}", text):
        return False
    return True

def dumpdata(url, data):
    pathlib.Path("output").mkdir(parents=True, exist_ok=True)
    pathlib.Path("output/"+url).touch(exist_ok=True)
    with open("output/"+url, "w") as f:
        data["id"] = url
        json.dump(data, f)