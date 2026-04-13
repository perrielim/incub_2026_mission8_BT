cmake_minimum_required(VERSION 3.16)
project(bt_mission_prototype CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(BUILD_TESTING OFF CACHE BOOL "Disable BT.CPP tests" FORCE)

add_subdirectory(/workspace/BehaviorTree.CPP /workspace/BehaviorTree.CPP/build_from_app)

add_executable(bt_runner
  src/main.cpp
  src/nodes_basic.cpp
)

target_include_directories(bt_runner PRIVATE /workspace/BehaviorTree.CPP/include)
target_link_libraries(bt_runner PRIVATE behaviortree_cpp)