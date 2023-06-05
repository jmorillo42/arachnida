#!/Users/jmorillo/Documents/cyber-camp/.py37env/bin/python

import argparse
import collections
import os
import pathlib
import posixpath
import sys
import time
import typing
import urllib.parse as urlparse

import bs4
import filetype
import requests

MIME_EXT = {
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/bmp',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/pdf'
}


class SpiderError(Exception):
    pass


class UrlScraped:
    def __init__(self):
        self.url_visited = set()
        self.url_pending: typing.Dict[int, typing.Set[str]] = collections.defaultdict(set)

    def add(self, url: str, level: int):
        if url not in self.url_visited and not self.contains(url):
            self.url_pending[level].add(url)

    def next(self) -> typing.Optional[typing.Tuple[str, int]]:
        if self.is_empty():
            return None
        level = min(self.url_pending)
        url = self.url_pending[level].pop()
        self.url_visited.add(url)
        if not self.url_pending[level]:
            del self.url_pending[level]
        return url, level

    def is_empty(self):
        return not self.url_pending

    def contains(self, url):
        for level in self.url_pending:
            if url in self.url_pending[level]:
                return True
        return False


class Spider:
    def __init__(self, url, recursive: bool = False, level: int = 5, path: str = './data/'):
        url_parsed = urlparse.urlparse(url)
        self.__is_file = url_parsed.scheme == 'file'
        self.__domain = url_parsed.netloc
        if self.__is_file and (url_parsed.netloc or url_parsed.path):
            self.url = url_parsed.netloc + url_parsed.path
        elif url_parsed.scheme in ('http', 'https') and url_parsed.netloc:
            self.url = url
        else:
            raise SpiderError('URL is not valid')
        self.recursive = recursive
        if not recursive or self.__is_file:
            self.level = 1
        elif level >= 0:
            self.level = level
        else:
            raise SpiderError('Level must be a positive number')
        try:
            pathlib.Path(path).resolve()
            self.path: str = os.path.abspath(os.path.expanduser(path))
            os.makedirs(self.path, exist_ok=True)
        except (OSError, RuntimeError):
            raise SpiderError('Path is not valid')
        self.__url_scraped = UrlScraped()
        self.__image_urls: typing.Optional[typing.Set[str]] = set()

    def get_images(self) -> typing.Set[str]:
        if self.__image_urls:
            return self.__image_urls
        self.__url_scraped.add(self.url, 1)
        while not self.__url_scraped.is_empty():
            url, level = self.__url_scraped.next()
            self.__parse_new_url(url, level)
        print()
        return self.__image_urls

    def write_images(self) -> None:
        if self.__image_urls is None:
            self.get_images()
        for img_url in self.__ft_progress(self.__image_urls):
            try:
                img_req = requests.get(img_url, timeout=(3, 7), headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:78.0) Gecko/20100101 Firefox/78.0', })
            except requests.exceptions.RequestException:
                print(f'Warning: Image link "{img_url}" is not valid')
                continue
            if img_req.status_code != requests.codes.ok:
                print(f'Warning: Image link "{img_url}" is not valid')
                continue
            if img_req.content:
                file_type = filetype.guess(img_req.content)
                if file_type and file_type.mime in MIME_EXT:
                    filename, _ = os.path.splitext(posixpath.basename(urlparse.urlsplit(img_url).path))
                    filepath = os.path.join(self.path, f'{filename}.{file_type.extension}')
                    with open(filepath, 'wb') as img_file:
                        img_file.write(img_req.content)
        print()

    def __parse_new_url(self, url: str, level: int) -> None:
        try:
            html_text = self.__get_content(url)
            self.__get_urls(html_text, url, level)
        except SpiderError:
            print(f'Warning: URL "{url}" is not valid')

    def __get_content(self, url: str) -> str:
        if self.__is_file:
            with open(url) as html_file:
                return html_file.read()
        try:
            req = requests.get(url, timeout=(3, 7), headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:78.0) Gecko/20100101 Firefox/78.0', })
        except requests.exceptions.RequestException:
            raise SpiderError(f'Invalid URL: "{url}"') from None
        if req.status_code != requests.codes.ok:
            raise SpiderError('URL is not valid') from None
        return req.text

    def __get_urls(self, html: str, base_url: str, level: int) -> None:
        soup = bs4.BeautifulSoup(html, 'lxml')
        for img_tag in soup.find_all('img', {'src': True}):
            url_img = urlparse.urljoin(base_url, img_tag['src'])
            url_img_parsed = urlparse.urlparse(url_img)
            if url_img_parsed.scheme in ('http', 'https') and url_img_parsed.netloc:
                self.__image_urls.add(url_img)
        if self.level == 0 or level < self.level:
            for a_tag in soup.find_all('a', {'href': True}):
                page_url = urlparse.urljoin(base_url, a_tag['href'])
                page_url_parsed = urlparse.urlparse(page_url)
                if page_url_parsed.scheme in ('http', 'https'):
                    if page_url_parsed.path.endswith('.docx') or page_url_parsed.path.endswith('.pdf'):
                        self.__image_urls.add(page_url)
                    elif page_url_parsed.netloc == self.__domain:
                        self.__url_scraped.add(page_url, 0 if not self.level else level + 1)
        print(f'Level {level:02d} - Links: {len(self.__image_urls)}', end='\r')

    def __ft_progress(self, lst):
        start = time.perf_counter()
        for i, n in enumerate(lst, 1):
            elapsed = time.perf_counter() - start
            percentage = int(i * 100 / len(lst))
            eta = elapsed * (100 - percentage) / (percentage if percentage else 1)
            print(f'Saving files: {percentage:3}% - ETA: {eta:.2f}s ', end='\r')
            yield n


def get_args():
    parser = argparse.ArgumentParser(
        prog='Spider',
        description='The program "spider" allow you to extract all the images from a website, recursively, by providing a url as a parameter.',
        epilog='''The program manage the following options:
        ./spider [-rlp] URL
    • Option -r : recursively downloads the images in a URL received as a parameter.
    • Option -r -l [N] : indicates the maximum depth level of the recursive download. If not indicated, it will be 5.
    • Option -p [PATH] : indicates the path where the downloaded files will be saved. If not specified, ./data/ will be used.
    ''')
    parser.add_argument('-r',
                        action='store_true',
                        help='recursively downloads the images in a URL received as a parameter')
    parser.add_argument('-l',
                        type=int,
                        default=5,
                        help='indicates the maximum depth level of the recursive download. If not indicated, it will be 5.')
    parser.add_argument('-p',
                        type=str,
                        default='./data/',
                        help='indicates the path where the downloaded files will be saved. If not specified, ./data/ will be used.')
    parser.add_argument('url',
                        type=str,
                        metavar='URL')
    spider_args = parser.parse_args()
    if spider_args.l < 0:
        raise argparse.ArgumentError(None, message=f'argument -l: invalid positive value: "{spider_args.l}"')
    return spider_args


if __name__ == '__main__':
    sys.tracebacklimit = 0
    try:
        args = get_args()
    except argparse.ArgumentError as ex:
        raise SpiderError(ex.message) from None
    s = Spider(args.url, args.r, args.l, args.p)
    images = s.get_images()
    s.write_images()
