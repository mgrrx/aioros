# aioros
aioros is an anyio-based ROS client and master library

## Supported features
- Service Server
- Service Client
- Publisher
- Subscriber
- Support for sim_time
- Own ROS Master implementation

## Features which go beyond rospy
- Fully typed
- Unix Domain Socket transport as an optional feature (only works between aioros nodes)
- Multiple nodes within one executable

## TODO
- [ ] Parameter subscriptions for ROS Master
- [ ] Parameter subscriptions for ROS node
- [ ] ROS-style logging via /rosout
- [ ] Expose buffer sizes of publisher and subscriber
- [ ] More tests
- [ ] Documentation
- [ ] actionlib client
- [ ] actionlib server
- [ ] tf2 buffer client
- [ ] tf2 buffer support via own pybind11 wrapper due to https://github.com/ros/geometry2/blob/noetic-devel/tf2_py/src/tf2_py.cpp#L98-L102)
- [ ] GitHub actions