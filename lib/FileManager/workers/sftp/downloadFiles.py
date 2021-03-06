import os
import shutil
import subprocess
import traceback

from config.main import TMP_DIR
from lib.FileManager.workers.baseWorkerCustomer import BaseWorkerCustomer


class DownloadFiles(BaseWorkerCustomer):
    def __init__(self, paths, mode, session, *args, **kwargs):
        super(DownloadFiles, self).__init__(*args, **kwargs)

        self.download_dir = os.path.join(TMP_DIR, self.login, self.random_hash())

        self.paths = paths
        self.mode = mode
        self.session = session

    def run(self):
        try:
            # drop privileges
            self.preload()
            # prepare download dir strictly after dropping privileges
            if os.path.islink(self.download_dir):
                raise Exception('Symlinks are not allowed!')
            if not os.path.exists(self.download_dir):
                os.makedirs(self.download_dir)

            self.logger.info("DownloadFiles process run, %s" % self.paths)

            self.prepare_tmp_dir_and_archive(self.download_dir, self.get_ext(self.mode))

            success_paths, error_paths = self.copy_files_to_tmp(self.download_dir)

            if len(success_paths) == 1:
                one_file = True
            else:
                one_file = False

            download_path = None
            mtime = 0
            inode = 0
            size = 0

            if len(error_paths) == 0:  # Значит все хорошо, можно дальше обрабатывать
                if one_file is True:
                    if self.mode == "default":
                        download_path = os.path.join(self.download_dir, os.path.basename(success_paths[0]))
                    else:
                        download_path = self.download_dir.rstrip("/")
                        files_path = download_path
                        os.chdir(os.path.dirname(download_path))

                        if self.mode == 'zip':
                            zip_util = self.get_util('zip')
                            download_path = download_path + '.' + self.mode
                            return_code = subprocess.call([zip_util, '-r', download_path, os.path.basename(files_path)])
                            if return_code != 0:
                                raise Exception("Zip Error")
                        if self.mode == 'gzip':
                            tar_util = self.get_util('tar')
                            download_path += '.tar.gz'
                            return_code = subprocess.call(
                                    [tar_util, '-czf', download_path, os.path.basename(files_path)])
                            if return_code != 0:
                                raise Exception("Tar Error")

                        if self.mode == 'tar':
                            tar_util = self.get_util('tar')
                            download_path += '.tar'
                            return_code = subprocess.call(
                                    [tar_util, '-cf', download_path, os.path.basename(files_path)])
                            if return_code != 0:
                                raise Exception("Tar Error")

                        if self.mode == 'bz2':
                            tar_util = self.get_util('tar')
                            download_path += '.bz2'
                            return_code = subprocess.call(
                                    [tar_util, '-cjf', download_path, os.path.basename(files_path)])
                            if return_code != 0:
                                raise Exception("Tar Error")
                else:
                    download_path = self.download_dir.rstrip("/")
                    files_path = download_path
                    os.chdir(os.path.dirname(download_path))

                    if self.mode == 'zip' or self.mode == 'default':
                        zip_util = self.get_util('zip')
                        download_path = download_path + '.' + self.mode
                        return_code = subprocess.call([zip_util, '-r', download_path, os.path.basename(files_path)])
                        if return_code != 0:
                            raise Exception("Zip Error")

                    if self.mode == 'gzip':
                        tar_util = self.get_util('tar')
                        download_path += '.tar.gz'
                        return_code = subprocess.call([tar_util, '-czf', download_path, os.path.basename(files_path)])
                        if return_code != 0:
                            raise Exception("Tar Error")

                    if self.mode == 'tar':
                        tar_util = self.get_util('tar')
                        download_path += '.tar'
                        return_code = subprocess.call([tar_util, '-cf', download_path, os.path.basename(files_path)])
                        if return_code != 0:
                            raise Exception("Tar Error")

                    if self.mode == 'bz2':
                        tar_util = self.get_util('tar')
                        download_path += '.bz2'
                        return_code = subprocess.call([tar_util, '-cjf', download_path, os.path.basename(files_path)])
                        if return_code != 0:
                            raise Exception("Tar Error")

                file_info = os.lstat(download_path)

                mtime = int(file_info.st_ctime)
                inode = int(file_info.st_ino)
                size = int(file_info.st_size)

            print(download_path)

            result = {
                "success": success_paths,
                "errors": error_paths,
                "download_path": download_path,
                "file_name": os.path.basename(download_path),
                "mtime": mtime,
                "inode": inode,
                "size": size
            }

            self.on_success(result)

        except Exception as e:
            result = {
                "error": True,
                "message": str(e),
                "traceback": traceback.format_exc()
            }

            self.on_error(result)

    @staticmethod
    def get_util(name):
        p = os.popen('/bin/which ' + name, mode='r')
        s = p.readline().rstrip("\n")

        p.close()
        return s

    @staticmethod
    def get_ext(mode):
        ext = None

        if mode == 'zip':
            ext = '.zip'
        elif mode == 'gzip':
            ext = '.tar.gz'
        elif mode == 'tar':
            ext = '.tar'
        elif mode == 'bz2':
            ext = '.bz2'

        return ext

    @staticmethod
    def prepare_tmp_dir_and_archive(target_path, ext=None):
        if os.path.exists(target_path):
            shutil.rmtree(target_path)

        os.makedirs(target_path)

        if ext is not None and os.path.exists(target_path + ext):
            os.unlink(target_path + ext)

    def copy_files_to_tmp(self, target_path):
        success_paths = []
        error_paths = []

        sftp = self.get_sftp_connection(self.session)
        for path in self.paths:
            try:
                if sftp.rsync_from(path, target_path):
                    success_paths.append(path)
            except Exception as e:
                self.logger.error(
                    "Error copy %s , error %s , %s" % (str(path), str(e), traceback.format_exc()))
                error_paths.append(path)

        return success_paths, error_paths
