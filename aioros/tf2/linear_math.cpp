#include <sstream>
#include <pybind11/pybind11.h>
#include <tf2/LinearMath/Transform.h>
#include <tf2/LinearMath/Quaternion.h>

namespace py = pybind11;

PYBIND11_MODULE(_linear_math, module)
{
    py::class_<tf2::Quaternion>(module, "Quaternion")
        .def(py::init<const double &, const double &, const double &, const double &>())
        .def("__repr__", [](const tf2::Quaternion &self)
             {
                 std::ostringstream oss;
                 oss << "Quaternion(";
                 oss << "x=" << self.getX() << ", ";
                 oss << "y=" << self.getY() << ", ";
                 oss << "z=" << self.getZ() << ", ";
                 oss << "w=" << self.getW();
                 oss << ")";
                 return oss.str();
             })
        .def_property_readonly("x", &tf2::Quaternion::getX)
        .def_property_readonly("y", &tf2::Quaternion::getY)
        .def_property_readonly("z", &tf2::Quaternion::getZ)
        .def_property_readonly("w", &tf2::Quaternion::getW);

    py::class_<tf2::Vector3>(module, "Vector3")
        .def(py::init<const double &, const double &, const double &>())
        .def("__repr__", [](const tf2::Vector3 &self)
             {
                 std::ostringstream oss;
                 oss << "Vector3(";
                 oss << "x=" << self.getX() << ", ";
                 oss << "y=" << self.getY() << ", ";
                 oss << "z=" << self.getZ();
                 oss << ")";
                 return oss.str();
             })
        .def_property_readonly("x", &tf2::Vector3::getX)
        .def_property_readonly("y", &tf2::Vector3::getY)
        .def_property_readonly("z", &tf2::Vector3::getZ);

    py::class_<tf2::Transform>(module, "Transform")
        .def(py::init<const tf2::Quaternion &, const tf2::Vector3 &>())
        .def("__repr__", [](const tf2::Transform &self)
             {
                 std::ostringstream oss;
                 tf2::Quaternion q = self.getRotation();
                 const tf2::Vector3 &t = self.getOrigin();
                 oss << "Transform(";
                 oss << "rotation=Quaternion(";
                 oss << "x=" << q.x() << ", ";
                 oss << "y=" << q.y() << ", ";
                 oss << "z=" << q.z() << ", ";
                 oss << "w=" << q.w();
                 oss << "), ";
                 oss << "translation=Vector3(";
                 oss << "x=" << t.x() << ", ";
                 oss << "y=" << t.y() << ", ";
                 oss << "z=" << t.z();
                 oss << "))";
                 return oss.str();
             })
        .def_property_readonly("rotation", &tf2::Transform::getRotation)
        .def_property_readonly("translation", [](const tf2::Transform &self)
                               { return self.getOrigin(); })
        .def("__matmul__", [](const tf2::Transform &self, const tf2::Transform &other)
             { return self * other; })
        .def("__matmul__", [](const tf2::Transform &self, const tf2::Vector3 &other)
             { return self * other; });
}