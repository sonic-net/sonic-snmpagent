"""Keep the local fixture package lock separate from the shared toolchain lock."""

load("@rules_distroless//apt:extensions.bzl", _apt = "apt")

apt = _apt
