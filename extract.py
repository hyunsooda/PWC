import os
import shutil
import bs4
import re
import requests
import argparse
import torch.multiprocessing as mp
from PyPDF2 import PdfReader
from model.llm import ask, init_model, repo_system_prompt
from io import BytesIO

N_CHUNKS = 1
ALLOWED_MAX_SIZE = 20000000
WEB_URL_REGEX = r"""(?i)\b((?:https?:(?:/{1,3}|[a-z0-9%])|[a-z0-9.\-]+[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)/)(?:[^\s()<>{}\[\]]+|\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\))+(?:\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’])|(?:(?<!@)[a-z0-9]+(?:[.\-][a-z0-9]+)*[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)\b/?(?!@)))"""
GITHUB = 'github.com'
GITLAB = 'gitlab.com'

def mkdir_overwrite(dir):
    if os.path.exists(dir):
        shutil.rmtree(dir)
    os.makedirs(dir)

def write_file(dir, filename, repolinks):
    with open(os.path.join(dir, filename.replace('/', '_')), "w") as file:
        file.write(repolinks)

def isMatch(str, prefix):
    for p in prefix:
        if p in str:
            return True
    return False

def extractURLs(refs, prefix):
    urls = []
    matches = re.findall(WEB_URL_REGEX, refs)
    for m in matches:
        if isMatch(m, prefix):
            m = m.split(',', 1)[0]
            if m.count('.') > 1:
                m = m.split('.')
                m.pop()
                m = '.'.join(m)
            if m.startswith('https://'):
                urls.append(m)
            else:
                urls.append('https://' + m)
    return urls

def read_pdf(model, tokenizer, url, title):
    data = requests.get(url)
    data.raise_for_status()
    reader = PdfReader(BytesIO(data.content))
    paper_text = ""

    for page in reader.pages:
        paper_text += page.extract_text() + "\n"

    repolinks = ask(model, tokenizer, repo_system_prompt, paper_text, 64)
    return repolinks

def fetch_usenix_sec_pdf(pdf_prefix, pt_link):
    resp = requests.get(pt_link)
    links = bs4.BeautifulSoup(resp.text, 'html.parser').select('a')
    for link in links:
        href = link.get('href')
        for prefix in pdf_prefix:
            if href != None and 'system/files/' + prefix in href:
                return href

def iterate_usenix_sec_papers(pdf_prefix, url):
    resp = requests.get(url)
    soup = bs4.BeautifulSoup(resp.text, 'html.parser')
    links = soup.select('a')
    pt = set([])
    papers = []
    for link in links:
        href = link.get('href')
        if href != None and not 'https://' in href and 'presentation' in href:
            pt_link = "https://www.usenix.org" + link.get('href')
            if not pt_link in pt:
                pt.add(pt_link)
                url = fetch_usenix_sec_pdf(pdf_prefix, pt_link)
                papers.append((link.get_text(), url))
    return papers

def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def work(idx, dir, model, tokenizer, workset):
    for title, url in workset:
        repolinks = read_pdf(model, tokenizer, url, title)
        write_file(dir, title, repolinks)
        print("processing {0}th ... {1}".format(idx, title))

def run(model, tokenizer, url, pdf_prefix, dir):
    mkdir_overwrite(dir)
    metadata = iterate_usenix_sec_papers(pdf_prefix, url)
    print("total " + str(len(metadata)) + " papers found")

    for idx, workset in enumerate(chunks(metadata, N_CHUNKS)):
        work(idx, dir, model, tokenizer, workset)

def parse_input(args):
    conference = args.conference.lower()
    year = args.year.lower()
    cycle = args.cycle.lower()
    output = args.output

    if int(year) < 2020:
        print('The year must be larger than 2020. The other years are not aware yet ({0})'.format(year))
        quit()

    if not (cycle == 'summer' or cycle == 'fall' or cycle == 'winter'):
        print('Unknown cycle: {0}'.format(cycle))
        quit()

    if conference == 'usenix':
        target_url = 'https://www.usenix.org/conference/usenixsecurity{0}/{1}-accepted-papers'.format(year[2:len(year)], cycle)
        pdf_prefix = ['sec{0}-'.format(year[2:len(year)]), 'usenixsecurity{0}-'.format(year[2:len(year)])]
        return target_url, pdf_prefix, output
    else:
        print('A conference (journal) {0} is not supported yet'.format(conference))
        quit()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--conference", dest="conference", required=True)
    parser.add_argument("-y", "--year", dest="year", required=True)
    parser.add_argument("-l", "--cycle", dest="cycle", required=True)
    parser.add_argument("-o", "--output", dest="output", required=True)
    parser.add_argument("-m", "--maxsize", dest="pdfsize", default=ALLOWED_MAX_SIZE)
    args = parser.parse_args()
    url, pdf_prefix, dir = parse_input(args)
    model, tokenizer = init_model("Qwen/Qwen2.5-1.5B-Instruct")
    run(model, tokenizer, url, pdf_prefix, dir)

if __name__ == "__main__":
    mp.set_start_method('spawn')
    main()
