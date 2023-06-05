#!/Users/jmorillo/Documents/cyber-camp/.py37env/bin/python

import argparse
import os
import os.path as os_path
import sys
from datetime import datetime

import PIL
import PIL.ExifTags as PILExifTags
import PIL.Image as PILImage
import docx
import filetype
import pypdf

MIME_EXT = {
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/bmp',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/pdf'
}


class ScorpionError(Exception):
    pass


class Scorpion:
    def __init__(self, file_paths: list):
        self.file_paths = file_paths

    def print(self):
        for file_path in self.file_paths:
            print(f'------- {os.path.split(file_path)[1]} -------')
            if not os_path.exists(file_path) or not os_path.isfile(file_path):
                print('  Error: file does not exist')
                continue
            if not os.access(file_path, os.R_OK):
                print('  Error: can not access file')
                continue
            file_type = filetype.guess(file_path)
            if file_type is None:
                print('  Error: unknown file type')
                continue
            elif file_type.mime not in MIME_EXT:
                print(f'  Error: MIME {file_type.mime} not supported')
                continue
            file_stat = os.stat(file_path)
            print(f'+ File size: {file_stat.st_size} bytes')
            print(
                f'+ Creation time: {datetime.fromtimestamp(file_stat.st_ctime).isoformat(sep=" ", timespec="minutes")}')
            print(
                f'+ Modification time: {datetime.fromtimestamp(file_stat.st_mtime).isoformat(sep=" ", timespec="minutes")}')
            if file_type.mime.startswith('image'):
                self.__img_metadata(file_path)
            elif file_type.mime.endswith('pdf'):
                self.__pdf_metadata(file_path)
            else:
                self.__doc_metadata(file_path)
            print()

    def __doc_metadata(self, doc_path):
        doc = docx.Document(doc_path)
        properties = doc.core_properties
        print(f'+ Author: {properties.author}')
        print(f'+ Category: {properties.category}')
        print(f'+ Comments: {properties.comments}')
        print(f'+ Content status: {properties.content_status}')
        print(f'+ Created: {properties.created}')
        print(f'+ Identifier: {properties.identifier}')
        print(f'+ Keywords: {properties.keywords}')
        print(f'+ Language: {properties.language}')
        print(f'+ Last modified by: {properties.last_modified_by}')
        print(f'+ Last printed: {properties.last_printed}')
        print(f'+ Modified: {properties.modified}')
        print(f'+ Revision: {properties.revision}')
        print(f'+ Subject: {properties.subject}')
        print(f'+ Title: {properties.title}')
        print(f'+ Version: {properties.version}')

    def __pdf_metadata(self, pdf_path):
        reader = pypdf.PdfReader(pdf_path)
        meta = reader.metadata
        print(f'+ Pages: {len(reader.pages)}')
        print(f'+ Author: {meta.author}')
        print(f'+ Creator: {meta.creator}')
        print(f'+ Producer: {meta.producer}')
        print(f'+ Subject: {meta.subject}')
        print(f'+ Title: {meta.title}')

    def __img_metadata(self, img_path):
        try:
            image = PILImage.open(img_path)
        except PIL.UnidentifiedImageError:
            print('  Error: unidentified image')
            return
        print(f'+ Format: {image.format}')
        print(f'+ Mode: {image.mode}')
        print(f'+ Size: {image.size}')
        print(f'+ Width: {image.width}')
        print(f'+ Height: {image.height}')
        for key, value in image.info.items():
            if key != 'exif':
                print(f'+ {key}: {value}')
        exif = image.getexif()
        if exif:
            print('+ Exif:')
            for key, value in exif.items():
                if key in PILExifTags.TAGS:
                    print(f'  - {PILExifTags.TAGS[key]}: {value}')
                elif key in PILExifTags.GPSTAGS:
                    print(f'  - {PILExifTags.GPSTAGS[key]}: {value}')
                else:
                    print(f'  - {key}: {value}')
        else:
            print('+ NO Exif')


def get_args():
    parser = argparse.ArgumentParser(
        prog='Scorpion',
        description='This program receive image files as parameters and parse them for EXIF and other metadata, displaying them on the screen.',
        epilog='''Scorpion manage the following options:
        ./scorpion FILE1 [FILE2 ...]
    ''')
    parser.add_argument('files', type=str, nargs='+', metavar='FILE')
    return parser.parse_args()


if __name__ == '__main__':
    sys.tracebacklimit = 0
    try:
        args = get_args()
    except argparse.ArgumentError as ex:
        raise ScorpionError(ex.message) from None
    s = Scorpion(args.files)
    s.print()
