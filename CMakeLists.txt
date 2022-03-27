cmake_minimum_required(VERSION 2.8.3)
project(aioros)

find_package(catkin REQUIRED COMPONENTS tf2)
find_package(pybind11 CONFIG REQUIRED)

catkin_python_setup()
catkin_package(
  CATKIN_DEPENDS tf2
)

include_directories(${catkin_INCLUDE_DIRS})
add_library(aioros_tf2_buffer MODULE aioros/tf2/buffer_core.cpp)
target_link_libraries(aioros_tf2_buffer PUBLIC pybind11::module ${catkin_LIBRARIES})
add_dependencies(aioros_tf2_buffer ${catkin_EXPORTED_TARGETS})
set_target_properties(aioros_tf2_buffer PROPERTIES
  OUTPUT_NAME buffer_core PREFIX "_"
  ARCHIVE_OUTPUT_DIRECTORY ${CATKIN_DEVEL_PREFIX}/${CATKIN_PACKAGE_PYTHON_DESTINATION}
  LIBRARY_OUTPUT_DIRECTORY ${CATKIN_DEVEL_PREFIX}/${CATKIN_PACKAGE_PYTHON_DESTINATION}
  RUNTIME_OUTPUT_DIRECTORY ${CATKIN_DEVEL_PREFIX}/${CATKIN_PACKAGE_PYTHON_DESTINATION}
)

add_library(aioros_tf2_linear_math MODULE aioros/tf2/linear_math.cpp)
target_link_libraries(aioros_tf2_linear_math PUBLIC pybind11::module ${catkin_LIBRARIES})
add_dependencies(aioros_tf2_linear_math ${catkin_EXPORTED_TARGETS})
set_target_properties(aioros_tf2_linear_math PROPERTIES
  OUTPUT_NAME linear_math PREFIX "_"
  ARCHIVE_OUTPUT_DIRECTORY ${CATKIN_DEVEL_PREFIX}/${CATKIN_PACKAGE_PYTHON_DESTINATION}
  LIBRARY_OUTPUT_DIRECTORY ${CATKIN_DEVEL_PREFIX}/${CATKIN_PACKAGE_PYTHON_DESTINATION}
  RUNTIME_OUTPUT_DIRECTORY ${CATKIN_DEVEL_PREFIX}/${CATKIN_PACKAGE_PYTHON_DESTINATION}
)

install(
  FILES $<TARGET_FILE:aioros_tf2_buffer> $<TARGET_FILE:aioros_tf2_linear_math>
  DESTINATION ${CATKIN_PACKAGE_PYTHON_DESTINATION}/tf2/
)

catkin_install_python(
    PROGRAMS
     scripts/master
    DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

if (CATKIN_ENABLE_TESTING)
  find_program(PYTESTS NAMES
    "py.test${PYTHON_VERSION_MAJOR}.${PYTHON_VERSION_MINOR}"
    "py.test-${PYTHON_VERSION_MAJOR}.${PYTHON_VERSION_MINOR}"
    "py.test${PYTHON_VERSION_MAJOR}"
    "py.test-${PYTHON_VERSION_MAJOR}"
    "py.test"
    "pytest${PYTHON_VERSION_MAJOR}.${PYTHON_VERSION_MINOR}"
    "pytest-${PYTHON_VERSION_MAJOR}.${PYTHON_VERSION_MINOR}"
    "pytest${PYTHON_VERSION_MAJOR}"
    "pytest-${PYTHON_VERSION_MAJOR}"
    "pytest")
  if(PYTESTS)
    message(STATUS "Using Python pytest: ${PYTESTS}")

    set(output_path ${CATKIN_TEST_RESULTS_DIR}/${PROJECT_NAME})
    get_filename_component(output_path "${output_path}" ABSOLUTE)
    set(cmd "${CMAKE_COMMAND} -E make_directory ${output_path}")

    set(cmd ${cmd} "${PYTESTS} ${PROJECT_SOURCE_DIR}/tests --junit-xml=${output_path}/pytests-tests.xml")

    catkin_run_tests_target("pytests" tests "pytests-tests.xml" COMMAND ${cmd})

  else()
    message(STATUS "pytests not found, Python tests can not be run (try installing package 'python3-pytest')")
  endif()
endif()