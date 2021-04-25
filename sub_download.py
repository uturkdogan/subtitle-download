#!/usr/bin/env python

import os
import json
import logging
import glob
import argparse


from pythonopensubtitles.opensubtitles import OpenSubtitles
from pythonopensubtitles.utils import File

from ffsubsync import ffsubsync

LANGUAGE_ID = 'eng'

class SubtitleNotFoundException(Exception):
    pass

class SubDownloader():

    def __init__(self):
        self.logger = logging.getLogger('downloader')
        credentials = self.get_credentials()
        self.ost = OpenSubtitles()
        self.ost.login(credentials['username'],
                       credentials['password'])
        self.logger.info('Successfully logged in to ost.')

    def get_credentials(self):
        """
        Gets credentials from credentials.json
        """
        try:
            with open('credentials.json') as f:
                credentials = json.load(f)
            assert 'username' in credentials, "Json file doesn't have username"
            assert 'password' in credentials, "Json file doesn't have password"
            return credentials
        except:
            self.logger.exception("Make sure to rename example_credentials.json and fill the information")
            raise

    def download_subtitle(self, file_path: str) -> str:
        """
        Downloads subtitle and returns the path of it.
        """
        file_object = File(file_path)
        file_hash = file_object.get_hash()
        file_size = file_object.size
        file_name_without_extension = os.path.splitext(file_path)[0]
        file_name = os.path.basename(file_path)
        file_folder = os.path.dirname(file_path)
        self.logger.info(f'Searching subtitles for {file_name}')
        # I could technically search for multiple of files.
        # But free api has limitations, so wouldn't have helped much.
        subtitles = self.ost.search_subtitles([
            {
                'sublanguageid': LANGUAGE_ID,
                'moviehash': file_hash,
                'moviebytesize': file_size,
            }
        ])
        self.logger.debug(f"{len(subtitles)} found for {file_name}")
        if not subtitles:
            raise SubtitleNotFoundException(f"No subtitles were found for {file_name}")
        subtitle_id = subtitles[0].get('IDSubtitleFile')
        paths = self.ost.download_subtitles([subtitle_id], output_directory=file_folder, extension='srt')
        subtitle_filename = paths.get(subtitle_id)
        if not subtitle_filename:
            raise SubtitleNotFoundException(f"Subtitle download was failed for {file_name}")
        os.rename(subtitle_filename, f"{file_name_without_extension}.en.srt")
        return f"{file_name_without_extension}.en.srt"

    def sync_subtitles(self, reference: str, subtitle: str):
        """
        Syncs the subtitles to reference
        """
        parser = ffsubsync.make_parser()
        args = parser.parse_args([reference, '-i', subtitle, '--overwrite-input'])
        result = ffsubsync.run(args)
        self.logger.info(f"{reference} subtitle sync completed with:\n{result['retval']}")

    def process_file(self, file_path: str):
        """
        Download subtitles for the file and sync the subtitles
        """
        subtitle = self.download_subtitle(file_path)
        self.sync_subtitles(file_path, subtitle)

    def process_glob(self, files: [str]):
        for file_ in files:
            try:
                self.process_file(file_)
            except SubtitleNotFoundException:
                self.logger.exception(f"skipping {file_}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs='+', help="Unix Glob to find files with. Recomended to use extension as well.")
    args = parser.parse_args()
    sd = SubDownloader()
    sd.process_glob(args.files)

if __name__ == '__main__':
    main()
