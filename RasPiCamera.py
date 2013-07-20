#! /usr/bin/python

import logging
import optparse, ConfigParser

import gdata.photos.service
import time, os, subprocess, tempfile
from PIL import Image
import threading, Queue
from datetime import datetime

                 

# thread that runs in the background uploading pics to Picasa
class background_upload(threading.Thread):
    def __init__ (self, picasa, album_url, q, myname):
        self.picasa = picasa
        self.album_url = album_url
        self.q = q
        threading.Thread.__init__ (self)
        self.daemon = True
        self.myname = myname

    def check_type(self, filehandle):
        extension = os.path.splitext(filehandle.name)[1][1:]
        if (extension == 'jpg'):
            pic_type='image/jpeg'
        else:
            pic_type='image/bmp'

        return pic_type
    

    def run(self):
        while True:
            logging.debug("%s Wait on queue" % self.myname)
            filehandle = self.q.get()
            logging.debug("%s: popped one off the queue" % self.myname)
            pic_type = self.check_type(filehandle)
            photo = self.picasa.InsertPhotoSimple(self.album_url,
                                                  'Movement Detected',
                                                  '',
                                                  filehandle,
                                                  content_type=pic_type)
            logging.debug("%s: Pic uploaded to Picasa" % self.myname)


# reads config parameters from config.ini
class ConfigRead:
    def __init__(self, filepath):
        config = ConfigParser.ConfigParser()
        # read contents of config.ini from the same directory as the script itself
        config.read(filepath)

        self.email    = config.get('LOGIN','email')
        self.password = config.get('LOGIN','password')
        self.username = config.get('LOGIN','username')
        self.album_name = config.get('LOGIN','album_name')
        
        self.loop_hrs = config.getint('CONFIG','hrs_to_loop')

        # currently unused. Maybe useful at some later point.
        self.interval = config.getint('CONFIG','interval')
            
        self.threshold = config.getint('CONFIG','picture_threshold')
        self.sensitivity = config.getint('CONFIG','picture_sensitivity')
        self.forceCaptureTime = config.getint('CONFIG','forceCaptureTime')
        self.upload_scratch_pics = config.getboolean('CONFIG','upload_scratch_pics')

        self.upload_quality = config.getint('PICTURE','upload_quality')
        self.rotation = config.getint('PICTURE','camera_rotation')

# This class handles the gdata login + album id extraction gubbins
class PicasaLogin:
    def __init__(self, email, password, username):
        self.username = username

        try:
            self.picasa = gdata.photos.service.PhotosService(email=email,
                                                password=password)
            self.picasa.ProgrammaticLogin()
        except GooglePhotosException as gpe:
            logging.critical("Picasa Login failed!")
            sys.exit(gpe.message)
    
    def get_album_url(self, album_name):
        albums = self.picasa.GetUserFeed(user=self.username)
        album_url = None
           
        for album in albums.entry:
          if album.title.text==album_name:
            album_url = '/data/feed/api/user/default/albumid/%s' % (album.gphoto_id.text)
        
        # if the album does not exist, create it!    
        if (album_url == None):
            logging.info('Creating Album: %s ' % album_name)
            try:
                album = self.picasa.InsertAlbum(title=album_name, summary="",access='private')
                album_url = '/data/feed/api/user/default/albumid/%s' % (album.gphoto_id.text)
            except GooglePhotosException as gpe:
                logging.critical("Album creation failed!")
                sys.exit(gpe.message)

        return album_url

# Capture a small test image (for motion detection)
def captureTestImage(rotation):
    command = "raspistill -rot %s -w %s -h %s -t 0 -e bmp -o -" % (rotation, 100, 75)
    temp_file = tempfile.NamedTemporaryFile(suffix='.bmp')
    temp_file.write(subprocess.check_output(command, shell=True))
    temp_file.seek(0)
    im = Image.open(temp_file)
    buffer = im.load()
    return im, buffer, temp_file

# capture and upload a full size image to Picasa
def uploadImage(queue, rotation, upload_quality):
    command = "raspistill -rot %s -w 2048 -h 1536 -t 0 -e jpg -q %s -o -" % \
                                                            (rotation, upload_quality)
    temp_file = tempfile.NamedTemporaryFile(suffix='.jpg')
    temp_file.write(subprocess.check_output(command, shell=True))
    temp_file.seek(0)
    logging.debug("hirez queue push")
    queue.put(temp_file)
    


# sets up default logging levels based on command line parameters
# based on code from:
# http://web.archive.org/web/20120819135307/http://aymanh.com/python-debugging-techniques

LOGGING_LEVELS = {'critical': logging.CRITICAL,
                  'error': logging.ERROR,
                  'warning': logging.WARNING,
                  'info': logging.INFO,
                  'debug': logging.DEBUG}
                  
def loglvl_setup():
    parser = optparse.OptionParser()
    parser.add_option('-l', '--logging-level', help='Logging level')
    parser.add_option('-f', '--logging-file', help='Logging file name')
    (options, args) = parser.parse_args()
    logging_level = LOGGING_LEVELS.get(options.logging_level, logging.NOTSET)
    logging.basicConfig(level=logging_level, filename=options.logging_file,
                      format='%(asctime)s %(levelname)s: %(message)s',
                      datefmt='%Y-%m-%d %H:%M:%S')


def main():
    loglvl_setup()
    
    logging.debug("Starting up....")
    # config.ini should be in the same location as the script
    # get script path with some os.path hackery
    config = ConfigRead(os.path.join(
                        os.path.dirname(
                        os.path.realpath(
                        __file__)),
                        'config.ini'))

    start_time = datetime.now().time().hour 
    cur_time = datetime.now().time().hour

    logging.debug("Login to Picasa")
    gdata_login = PicasaLogin(config.email, config.password, config.username)
    album_url = gdata_login.get_album_url(config.album_name)

    
    upload_queue = Queue.Queue()
    uploadThread = background_upload(gdata_login.picasa, 
                                     album_url, 
                                     upload_queue, 
                                     "FullUploader")
    uploadThread.start()
    
    # do we need to upload the 100x75 thumbnails too?
    # If so spawn another thread + queue to handle that
    if (config.upload_scratch_pics):
        album_url_thumbs = gdata_login.get_album_url(config.album_name + "_thumbs")
        upload_queue_thumbs = Queue.Queue()
        uploadThread_thumbs = background_upload(gdata_login.picasa, 
                                                album_url_thumbs, 
                                                upload_queue_thumbs, 
                                                "ThumbUploader")
        uploadThread_thumbs.start()
        

    #get an image to kick the process off with
    image1, buffer1, file_handle = captureTestImage(config.rotation)

    # Reset last capture time
    lastCapture = time.time()

    # main loop
    # original motion detection code from 
    # http://www.raspberrypi.org/phpBB3/viewtopic.php?p=358259#p362915
    # TODO: requires cleanup
    while (cur_time - start_time < config.loop_hrs):
        # Get comparison image
        logging.debug("Current queue size FullUp:%d ThumbUp:%d" % \
                                (upload_queue.qsize(), upload_queue_thumbs.qsize()))
        image2, buffer2, file_handle = captureTestImage(config.rotation)
        
        # Count changed pixels
        changedPixels = 0
        for x in xrange(0, 100):
            # Scan one line of image then check sensitivity for movement
            for y in xrange(0, 75):
                # Just check green channel as it's the highest quality channel
                pixdiff = abs(buffer1[x,y][1] - buffer2[x,y][1])
                if pixdiff > config.threshold:
                    changedPixels += 1

            # If movement sensitivity exceeded, upload image and
            # Exit before full image scan complete
            if changedPixels > config.sensitivity:
                if (config.upload_scratch_pics):
                    logging.debug("low rez queue push")
                    upload_queue_thumbs.put(file_handle)
                lastCapture = time.time()
                uploadImage(upload_queue, config.rotation, config.upload_quality)
                break
            continue    
        
        # Check force capture
        if time.time() - lastCapture > config.forceCaptureTime:
            logging.debug("Force an upload next round")
            changedPixels = config.sensitivity + 1            

        # Swap comparison buffers
        image1  = image2
        buffer1 = buffer2
        
        cur_time = datetime.now().time().hour


if __name__ == '__main__':
    main()
