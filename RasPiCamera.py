#! /usr/bin/python

import logging
import optparse, ConfigParser
import time, os, subprocess, tempfile, cStringIO
import threading, Queue

import gdata.photos.service
from PIL import Image

                 

class BackgroundUpload(threading.Thread):
    """thread that runs in the background uploading pics to Picasa"""
    def __init__ (self, picasa, album_url, q, myname):
        self.picasa = picasa
        self.album_url = album_url
        self.q = q
        threading.Thread.__init__ (self)
        self.daemon = True
        self.myname = myname

    def check_type(self, filehandle):
        """
        Calling:
        extension = os.path.splitext(filehandle.name)[1][1:]
        would be nice, but won't work on a StringIO buffer. Take the lazy
        option and if it's a StringIO buffer, assume it's a bmp :)
        we could, of course, just use self.myname; but I'd rather use that
        just for debug (and remove self.myname sometime in future.)
        """
        
        if (isinstance(filehandle, cStringIO.OutputType)):
            pic_type='image/bmp'
        else:
            pic_type='image/jpeg'

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


class ConfigRead:
    """reads config parameters from config.ini"""
    def __init__(self, filepath):
        config = ConfigParser.ConfigParser()
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


class PicasaLogin:
    """This class handles the gdata login + album id extraction gubbins"""
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
def capture_test_image(rotation):
    command = "raspistill -rot %s -w %s -h %s -t 0 -e bmp -o -" % (rotation, 100, 75)
    # StringIO used here as to not wear out the SD card
    # There will be a lot of these pics taken
    imageData = cStringIO.StringIO()
    imageData.write(subprocess.check_output(command, shell=True))
    imageData.seek(0)
    im = Image.open(imageData)
    buffer = im.load()
    return buffer, imageData

# capture full-size image and add it to the queue for background upload
def upload_image(queue, rotation, upload_quality):
    command = "raspistill -rot %s -w 2048 -h 1536 -t 0 -e jpg -q %s -o -" % \
                                                            (rotation, upload_quality)
    """
    These files are >1.5Mb in size and the upload happens in a background thread. 
    We can't get the background thread to take the picture as only one thread can
    access the camera. So we take the picture here and send just the handle to the 
    background thread.
    Using a StringIO here (like above, to save disk writes) would be a bad idea for
    two reasons:
    (a) Now we need to send the entire StringIO buffer via the queue
        Large memory consumption (compared to the 100x75 pics above)
    (b) The upload takes a lot of time and if there is lots of motion, there
        will be lots of items in the queue. Again, allowing the memory 
        consumption to spiral out of control
    
    So, use a tempfile, which does write to disk, but it auto cleans up/deletes
    after the filehandle goes out of scope
    """
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
    logging_level = LOGGING_LEVELS.get(options.logging_level, logging.WARNING)
    logging.basicConfig(level=logging_level, filename=options.logging_file,
                  format='%(asctime)s %(levelname)s: %(message)s',
                  datefmt='%Y-%m-%d %H:%M:%S')


def main():
    loglvl_setup()
    
    logging.debug("Starting up....")
    # config.ini should be in the same location as the script
    # get script path with some os.path hackery
    config_ini_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),'config.ini')
    config = ConfigRead(config_ini_path)

    end_time = time.time() + (config.loop_hrs*60*60)

    logging.debug("Login to Picasa")
    gdata_login = PicasaLogin(config.email, config.password, config.username)
    album_url = gdata_login.get_album_url(config.album_name)

    
    logging.debug("Setup Threads & Queues")
    upload_queue = Queue.Queue()
    uploadThread = BackgroundUpload(gdata_login.picasa, 
                                     album_url, 
                                     upload_queue, 
                                     "FullUploader")
    uploadThread.start()
    
    # do we need to upload the 100x75 thumbnails too?
    # If so spawn another thread + queue to handle that
    if (config.upload_scratch_pics):
        album_url_thumbs = gdata_login.get_album_url(config.album_name + "_thumbs")
        upload_queue_thumbs = Queue.Queue()
        uploadThread_thumbs = BackgroundUpload(gdata_login.picasa, 
                                                album_url_thumbs, 
                                                upload_queue_thumbs, 
                                                "ThumbUploader")
        uploadThread_thumbs.start()
    else :
        # This just helps with logging logic later in the code
        upload_queue_thumbs = 0
        

    #get an image to kick the process off with
    buffer1, file_handle = capture_test_image(config.rotation)

    # Reset last capture time
    lastCapture = time.time()

    # main loop
    # original motion detection code from 
    # http://www.raspberrypi.org/phpBB3/viewtopic.php?p=358259#p362915
    # TODO: requires cleanup
    logging.debug("Main Loop start")
    while (time.time() < end_time):
        # Get comparison image
        logging.debug("Current queue size FullSize:%d ThumbSize:%d" % \
                                   (upload_queue.qsize(), 
                                   (upload_queue_thumbs.qsize() if upload_queue_thumbs else 0) ))
        buffer2, file_handle = capture_test_image(config.rotation)
        
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
                    """
                    Note that we're going to dump the entire StringIO buffer 
                    into the queue for upload. As the picture size is 100x75, 
                    the upload's happen quickly; stopping the queue 
                    from consuming too much memory
                    """
                    upload_queue_thumbs.put(file_handle)
                lastCapture = time.time()
                # Take a full size picture and farm it off for background upload
                upload_image(upload_queue, config.rotation, config.upload_quality)
                break
            continue    
        
        # Check force capture
        if time.time() - lastCapture > config.forceCaptureTime:
            logging.debug("Force an upload next round")
            changedPixels = config.sensitivity + 1            

        # Swap comparison buffers
        buffer1 = buffer2


if __name__ == '__main__':
    main()
