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
    pythonpkg = python_version.withPackages (p: with p; [
      simpleaudio
      dbus-python
    ]);

    start = pkgs.writeShellScript "start" ''
      ${pythonpkg}/bin/python ./pomodoro.py $@
    '';

    deriv = pkgs.stdenv.mkDerivation rec {
      name = "pomodoro";
      src = ./.;

      phases = "installPhase";

      installPhase = let
        script = pkgs.writeShellApplication {
          inherit name;
          text = ''
            cd ${src}
            ${pythonpkg}/bin/python ./pomodoro.py "$@"
          '';
          runtimeInputs = [];
        };
      in ''
        ln -s ${script} $out
      '';
    };
  in {
    apps.${system}.default = {
      type = "app";
      program = "${start}";
    };
    packages.${system}.default = deriv;
    overlays.default = final: prev: {
      pomodoro = deriv;
    };
  };
}
