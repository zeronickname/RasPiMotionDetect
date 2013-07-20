Intro
-----

No matter what the project title says, this is *not* an intervalometer :)
It started off as one (check the history), but I pretty quickly came to the conclusion that without motion detection, a naive implementation of an intervalometer is kindof useless. You just wind up with either a lot of pictures, or you miss the really important ones.

So, this script now has some configurable parameters to tweak the motion sensitivity and as long as there is movement, it takes and uploads pics continuously to Picasa/Google Plus Photos.

Picasa was chosen as an endpoint because photos less than 2048x2048 do not count towards your storage.
Plus google kindly stitches together similar photos to create an animated gif, which is pretty awesome!

PreRequisites
--------------

* RaspberryPi with a camera board :)
* raspistill installed and configured (part of [RaspiCam](https://github.com/raspberrypi/userland/tree/master/host_applications/linux/apps/raspicam))

        http://www.raspberrypi.org/camera
        
* Python 2.x
* Python Imaging Library (PIL)

        apt-get install python-imaging
        
* gdata-python-client, downloaded and installed

        https://developers.google.com/gdata/articles/python_client_lib#library
        
TODO
----

Not a whole lot. It does what I want it to do. It would be nice to allow uploads to other online providers. The code could also do with a bit of a cleanup.
