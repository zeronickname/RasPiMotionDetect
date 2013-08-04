Intro
-----

This started off as a simple Intervalometer, but I pretty quickly came to the conclusion that without motion detection, a naive implementation of an intervalometer is kindof useless. You just wind up with either a lot of pictures, or you miss the really important ones.

So, this script now has some configurable parameters to tweak the motion sensitivity and as long as there is movement, it takes and uploads pics continuously to Picasa/Google Plus Photos. (python based motion detect code [originally from here](http://www.raspberrypi.org/phpBB3/viewtopic.php?p=358259#p362915)).

Picasa was chosen as an endpoint because photos less than 2048x2048 do not count towards your storage.
Plus google kindly stitches together similar photos to create an animated gif, which is pretty awesome!

Features
-----

* Configurable motion detection sesitivity.
* Automatically stop monitoring and exit after a set time (makes it easy to start from cron daily)
* Monitor only parts of the image for motion (thanks [Kesthal](http://www.raspberrypi.org/phpBB3/viewtopic.php?p=391583#p391583))
* Automatically create new albums on picasa every [1000 photos](https://support.google.com/picasa/answer/43879?hl=en-GB).


PreRequisites
--------------

* RaspberryPi with a camera board :)
* raspistill installed and configured (part of [RaspiCam](https://github.com/raspberrypi/userland/tree/master/host_applications/linux/apps/raspicam))

        http://www.raspberrypi.org/camera
        
* Python 2.x
* Python Imaging Library (PIL)

        apt-get install python-imaging-tk
        
* gdata-python-client, downloaded and installed

        https://developers.google.com/gdata/articles/python_client_lib#library
        
TODO
----

* It would be nice to allow uploads to other online providers.
* The code definitely needs a bit of a cleanup.
