#include <geometry_msgs/TransformStamped.h>
#include <tf2/buffer_core.h>
#include <tf2/exceptions.h>
#include <pybind11/pybind11.h>

namespace py = pybind11;

inline ros::Time time_from_python(py::object &time)
{
    return ros::Time(time.attr("secs").cast<uint32_t>(), time.attr("nsecs").cast<uint32_t>());
}

PYBIND11_MODULE(_buffer_core, module)
{
    auto base = py::register_exception<tf2::TransformException>(module, "TransformException");
    py::register_exception<tf2::ConnectivityException>(module, "ConnectivityException", base.ptr());
    py::register_exception<tf2::LookupException>(module, "LookupException", base.ptr());
    py::register_exception<tf2::ExtrapolationException>(module, "ExtrapolationException", base.ptr());
    py::register_exception<tf2::InvalidArgumentException>(module, "InvalidArgumentException", base.ptr());
    py::register_exception<tf2::TimeoutException>(module, "TimeoutException", base.ptr());

    py::object PyTransformStamped = py::module_::import("geometry_msgs.msg").attr("TransformStamped");

    py::class_<tf2::BufferCore>(module, "BufferCore")
        .def(py::init([](float &cache_time)
                      { return new tf2::BufferCore(ros::Duration(cache_time)); }),
             py::arg("cache_time") = 10.)
        .def("clear", &tf2::BufferCore::clear)
        .def("all_frames_as_string", &tf2::BufferCore::allFramesAsString)
        .def(
            "all_frames_as_yaml", [](tf2::BufferCore &self, double &current_time)
            { return self.allFramesAsYAML(current_time); },
            py::arg("current_time") = 0.0)
        .def(
            "lookup_transform", [PyTransformStamped](tf2::BufferCore &self, std::string &target_frame, std::string &source_frame, py::object time)
            {
                geometry_msgs::TransformStamped cpp = self.lookupTransform(target_frame, source_frame, time_from_python(time));
                py::object transform = PyTransformStamped();
                transform.attr("header").attr("frame_id") = cpp.header.frame_id;
                transform.attr("header").attr("stamp").attr("secs") = cpp.header.stamp.sec;
                transform.attr("header").attr("stamp").attr("nsecs") = cpp.header.stamp.nsec;
                transform.attr("child_frame_id") = cpp.child_frame_id;
                transform.attr("transform").attr("translation").attr("x") = cpp.transform.translation.x;
                transform.attr("transform").attr("translation").attr("y") = cpp.transform.translation.y;
                transform.attr("transform").attr("translation").attr("z") = cpp.transform.translation.z;
                transform.attr("transform").attr("rotation").attr("x") = cpp.transform.rotation.x;
                transform.attr("transform").attr("rotation").attr("y") = cpp.transform.rotation.y;
                transform.attr("transform").attr("rotation").attr("z") = cpp.transform.rotation.z;
                transform.attr("transform").attr("rotation").attr("w") = cpp.transform.rotation.w;
                return transform;
            })
        .def("lookup_transform_full", [PyTransformStamped](tf2::BufferCore &self, std::string &target_frame, py::object target_time, std::string &source_frame, py::object source_time, std::string fixed_frame)
             {
                 geometry_msgs::TransformStamped cpp = self.lookupTransform(target_frame, time_from_python(target_time), source_frame, time_from_python(source_time), fixed_frame);
                 py::object transform = PyTransformStamped();
                 transform.attr("header").attr("frame_id") = cpp.header.frame_id;
                 transform.attr("header").attr("stamp").attr("secs") = cpp.header.stamp.sec;
                 transform.attr("header").attr("stamp").attr("nsecs") = cpp.header.stamp.nsec;
                 transform.attr("child_frame_id") = cpp.child_frame_id;
                 transform.attr("transform").attr("translation").attr("x") = cpp.transform.translation.x;
                 transform.attr("transform").attr("translation").attr("y") = cpp.transform.translation.y;
                 transform.attr("transform").attr("translation").attr("z") = cpp.transform.translation.z;
                 transform.attr("transform").attr("rotation").attr("x") = cpp.transform.rotation.x;
                 transform.attr("transform").attr("rotation").attr("y") = cpp.transform.rotation.y;
                 transform.attr("transform").attr("rotation").attr("z") = cpp.transform.rotation.z;
                 transform.attr("transform").attr("rotation").attr("w") = cpp.transform.rotation.w;
                 return transform;
             })
        .def("can_transform", [](tf2::BufferCore &self, std::string &target_frame, std::string &source_frame, py::object time)
             { return self.canTransform(target_frame, source_frame, time_from_python(time)); })
        .def("can_transform_full", [](tf2::BufferCore &self, std::string &target_frame, py::object target_time, std::string &source_frame, py::object source_time, std::string fixed_frame)
             { return self.canTransform(target_frame, time_from_python(target_time), source_frame, time_from_python(source_time), fixed_frame); })
        .def(
            "set_transform", [](tf2::BufferCore &self, py::object &transform, std::string &authority, bool is_static)
            {
                geometry_msgs::TransformStamped cpp;
                cpp.header.stamp.sec = transform.attr("header").attr("stamp").attr("secs").cast<uint32_t>();
                cpp.header.stamp.nsec = transform.attr("header").attr("stamp").attr("nsecs").cast<uint32_t>();
                cpp.header.frame_id = transform.attr("header").attr("frame_id").cast<std::string>();
                cpp.child_frame_id = transform.attr("child_frame_id").cast<std::string>();
                cpp.transform.translation.x = transform.attr("transform").attr("translation").attr("x").cast<double>();
                cpp.transform.translation.y = transform.attr("transform").attr("translation").attr("y").cast<double>();
                cpp.transform.translation.z = transform.attr("transform").attr("translation").attr("z").cast<double>();
                cpp.transform.rotation.x = transform.attr("transform").attr("rotation").attr("x").cast<double>();
                cpp.transform.rotation.y = transform.attr("transform").attr("rotation").attr("y").cast<double>();
                cpp.transform.rotation.z = transform.attr("transform").attr("rotation").attr("z").cast<double>();
                cpp.transform.rotation.w = transform.attr("transform").attr("rotation").attr("w").cast<double>();

                self.setTransform(cpp, authority, is_static);
            },
            py::arg("transform"), py::arg("authority"), py::arg("is_static") = false);
};