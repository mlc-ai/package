set(CMAKE_PLATFORM Linux)
# this one is important
set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_PLATFORM Linux)
#this one not so much
set(CMAKE_SYSTEM_VERSION 1)

# specify the cross compiler
set(CMAKE_C_COMPILER $ENV{CC})

# where is the target environment
set(CMAKE_FIND_ROOT_PATH $ENV{PREFIX}
    $ENV{BUILD_PREFIX}/$ENV{HOST}/sysroot
    $ENV{BUILD_PREFIX})


# search for programs in the build host directories
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)

# We should be able to find othe libraries such as vulkan sdk
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)

# need both to get vulkan find path to work
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE BOTH)

# god-awful hack because it seems to not run correct tests to determine this:
set(__CHAR_UNSIGNED___EXITCODE 1)
