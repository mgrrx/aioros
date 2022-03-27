cmake_minimum_required(VERSION 2.8.3)
project(aioros)

find_package(catkin REQUIRED)

catkin_python_setup()
catkin_package()

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