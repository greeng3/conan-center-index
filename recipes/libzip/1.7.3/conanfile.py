import os
import stat
from conans import ConanFile, tools, CMake, AutoToolsBuildEnvironment
from conans.errors import ConanException


class LibZipConan(ConanFile):
    name = "libzip"
    version = "1.7.3"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://libzip.org/"
    license = "LibZip"
    description = "A C library for reading, creating, and modifying zip archives"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False], "minizip": [True, False]}
    default_options = {"shared": False, "fPIC": True, "minizip": False}
    exports = ["LICENSE"]
    exports_sources = ["CMakeLists.txt", "patches/**"]
    generators = "cmake"
    _source_subfolder = "source_subfolder"
    _build_subfolder = "build_subfolder"

    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_bzip2": [True, False],
        "with_openssl": [True, False],
        "with_mbedtls": [True, False],
        "enable_windows_crypto": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_bzip2": True,
        "with_mbedtls": True,
        "with_openssl": False,
        "enable_windows_crypto": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        else:
            del self.options.enable_windows_crypto

    def configure(self):
        del self.settings.compiler.libcxx
        del self.settings.compiler.cppstd

    def requirements(self):
        self.requires("zlib/1.2.11")
        self.requires("xz_utils/5.2.5@ggreene/test")
        if self.options.with_bzip2:
            self.requires("bzip2/1.0.8")
        if self.options.with_openssl:
            self.requires("openssl/1.0.2t")
        if self.options.with_mbedtls:
            self.requires("mbedtls/2.23.0-apache@ggreene/test")

    def source(self):
        tools.get(**self.conan_data["sources"][self.version])
        extracted_dir = self.name + "-" + self.version
        os.rename("{}-{}".format(self.name, self.version), self._source_subfolder)

    def _configure_cmake(self):
        cmake = CMake(self)
        cmake.definitions["ENABLE_MBEDTLS"] = self.options.with_mbedtls
        cmake.definitions["ENABLE_OPENSSL"] = self.options.with_openssl
        cmake.definitions["ENABLE_GNUTLS"] = False # TODO (uilian): We need GnuTLS package
        if self.settings.os == "Windows":
            cmake.definitions["ENABLE_WINDOWS_CRYPTO"] = self.options.enable_windows_crypto
        cmake.configure()
        return cmake

    def exclude_targets(self):
        cmake_file = os.path.join(self._source_subfolder, "CMakeLists.txt")
        excluded_targets = ["regress", "examples", "man"]
        for target in excluded_targets:
            try:
                tools.replace_in_file(cmake_file, "ADD_SUBDIRECTORY(%s)" % target, "")
            except ConanException:
                tools.replace_in_file(cmake_file, "add_subdirectory(%s)" % target, "")
        if self.options.with_openssl:
            tools.replace_in_file(cmake_file, "OPENSSL_LIBRARIES", "CONAN_LIBS_OPENSSL")
        if self.options.with_mbedtls:
            tools.replace_in_file(cmake_file, "MBEDTLS_LIBRARIES", "CONAN_LIBS_MBEDTLS")

    def build(self):
        for patch in self.conan_data.get("patches", {}).get(self.version, []):
            tools.patch(**patch)
        self.exclude_targets()
        cmake = self._configure_cmake()
        cmake.build()

    def package(self):
        cmake = self._configure_cmake()
        cmake.install()
        self.copy(pattern="LICENSE", dst="licenses", src=self._source_subfolder)

    def package_info(self):
        self.cpp_info.libs = tools.collect_libs(self)
        if self.settings.os == "Windows":
            if self.options.enable_windows_crypto:
                self.cpp_info.libs.append("bcrypt")

