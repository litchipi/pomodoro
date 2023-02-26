{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-22.11";
  };

  outputs = inputs: with inputs; let
    system = "x86_64-linux";
    pkgs = import nixpkgs { inherit system; };
    lib = pkgs.lib;

    python_version = pkgs.python310;
    python_packages_version = pkgs.python310Packages;
    custom_pkgs = (import ./python-packages.nix pkgs python_packages_version);
    pythonpkg = python_version.withPackages (p: with p; [
      simpleaudio
      dbus-python
    ]);

    start = pkgs.writeShellScript "start" ''
      ${pythonpkg}/bin/python ./pomodoro.py $@
    '';

  in {
    apps.${system}.default = {
      type = "app";
      program = "${start}";
    };
  };
}
