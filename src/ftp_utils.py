import ftplib
import logging


logger = logging.getLogger(__name__)


def upload(f, ftp_host, ftp_port=21, ftp_username=None, ftp_password=None,
        ftp_filename='tmp', upload_path='/tmp', timeout=None):
    logger.info('FTP::Upload: host={host} username={username} port={port}'
        .format(host=ftp_host, port=ftp_port, username=ftp_username)
    )
    ftp = ftplib.FTP(ftp_host)
    res = ftp.login(ftp_username, ftp_password)
    logger.info('FTP::Login: %s' % res)
    ftp.cwd(upload_path)
    print ftp.storbinary('STOR %s' % ftp_filename, f)



if __name__ == '__main__':
    with open('src/ftp_utils.py', 'rb') as f:
        upload(f, '192.168.1.96', ftp_username='jesse', ftp_password='ratmaxi8', path='/home/jesse/Workspace')
