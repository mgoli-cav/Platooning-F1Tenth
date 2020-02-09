#!/usr/bin/env python
import rospy
import cv2
from std_msgs.msg import String
from sensor_msgs.msg import Image, CompressedImage
from cv_bridge import CvBridge, CvBridgeError
from message_filters import ApproximateTimeSynchronizer, Subscriber
from ackermann_msgs.msg import AckermannDriveStamped
import imutils

from race.msg import drive_param


class MessageSynchronizer:
    ''' Gathers messages with vehicle information that have similar time stamps

        /camera/zed/rgb/image_rect_color/compressed: 18 hz
        /camera/zed/rgb/image_rect_color: 18 hz
        /racecar/drive_parameters: 40 hz
    '''
    def __init__(self):
        self.image_rect_color=Subscriber('/racecar/camera/zed/rgb/image_rect_color',Image)
        self.image_rect_color_cp=Subscriber('/racecar/camera/zed/rgb/image_rect_color/compressed',CompressedImage)
        self.drive_parameters=Subscriber('/racecar/drive_parameters',drive_param)
        self.ackermann_stamped=Subscriber('vesc/ackermann_cmd_mux/input/teleop',AckermannDriveStamped)
        self.cv_bridge=CvBridge()

        #create the time synchronizer
        self.sub = ApproximateTimeSynchronizer([self.image_rect_color,self.image_rect_color_cp,self.ackermann_stamped], queue_size = 20, slop = 0.049)
        #register the callback to the synchronizer
        self.sub.registerCallback(self.master_callback)

    #callback for the synchronized messages
    def master_callback(self,image,image_cp,ackermann_msg): #drive_param):
        #convert rosmsg to cv image
        try:
            cv_image=self.cv_bridge.imgmsg_to_cv2(image,"bgr8")
            cv_image=self.preprocess_image(cv_image,66,200)
        except CvBridgeError as e:
            print(e)
        print(cv_image.shape,(ackermann_msg.drive.speed,ackermann_msg.drive.steering_angle))
        cv2.imshow("Current Image",cv_image)
        cv2.waitKey(5)

    #preprocess the images so that the DAEV model can use them
    #inspired by Adrian Rosebrock
    def preprocess_image(self,image,height,width):
        (h,w)=image.shape[:2]

        #if the width is greater than the height then resize along the width
        if w>h:
            image= imutils.resize(image,width=width)
        #otherwise the height is greater than the width so resize along the height
        else: 
            image=imutils.resize(image,height=height)

        #now that we have enlargened or shrunk the image to the size of our choice
        #need to fix the other dimensions

        #Deterime the padding values for the width and the height to obtain the target dimensions
        #One of these is gonna be zero from above.
        padW=int((width-image.shape[1])/2.0)
        padH=int((width-image.shape[0])/2.0)

        #pad the image then apply one more resizing to handle any rounding issues.
        #There will be cases where we are one pixel off
        #the padding order is top, bottom, left,right
        image=cv2.copyMakeBorder(image,padH,padH,padW,padW,cv2.BORDER_REPLICATE)
        image=cv2.resize(image,(width,height))
        return image


if __name__=='__main__':
    rospy.init_node('image_command_sync')
    
    #initialize the message filter
    mf=MessageSynchronizer()
    #rospy.Subscriber(il.image_topic,drive_param,mf.print_cb)
    #spin so that we can receive messages
    rospy.spin()    