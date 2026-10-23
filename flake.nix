{
  description = "Modular 16x2 LCD display manager (VU meter, Niri window, …)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };

        python = pkgs.python312;

        # Runtime + build deps
        pythonEnv = python.withPackages (ps: with ps; [
          pyserial
          sounddevice
          numpy
          psutil
          setuptools
        ]);

        lcd-display = python.pkgs.buildPythonApplication {
          pname = "lcd-display";
          version = "0.1.0";
          src = ./.;
          format = "pyproject";

          propagatedBuildInputs = with python.pkgs; [
            pyserial
            sounddevice
            numpy
            psutil
          ];

          # sounddevice needs PortAudio at runtime
          buildInputs = [ pkgs.portaudio ];
          nativeBuildInputs = [ pkgs.makeWrapper ];

          # Make sure libportaudio is findable
          postInstall = ''
            wrapProgram $out/bin/lcd-display \
              --prefix LD_LIBRARY_PATH : ${pkgs.portaudio}/lib
          '';

          meta = with pkgs.lib; {
            description = "Modular 16x2 LCD display manager";
            license = licenses.mit;
            platforms = platforms.linux;
          };
        };

        # Systemd user unit as a simple derivation that can be installed
        systemdUnit = pkgs.writeTextFile {
          name = "lcd-display.service";
          text = ''
            [Unit]
            Description=LCD Display Manager (16x2)
            After=graphical-session.target
            PartOf=graphical-session.target

            [Service]
            ExecStart=${lcd-display}/bin/lcd-display --display vu
            Restart=on-failure
            RestartSec=3
            # Pass through the Niri socket and runtime dir
            PassEnvironment=NIRI_SOCKET XDG_RUNTIME_DIR

            [Install]
            WantedBy=graphical-session.target
          '';
          destination = "/lcd-display.service";
        };

      in {
        packages = {
          default = lcd-display;
          lcd-display = lcd-display;
          # Convenience: the unit file itself
          service = systemdUnit;
        };

        # Dev shell with everything needed to hack on the code
        devShells.default = pkgs.mkShell {
          name = "lcd-display-dev";
          buildInputs = [
            pythonEnv
            pkgs.portaudio
            pkgs.pkg-config
            pkgs.systemd          # for systemctl while testing
          ];
          shellHook = ''
            echo "lcd-display dev shell"
            echo "  python -m lcd_display --list"
            echo "  python -m lcd_display --display vu"
            export PYTHONPATH="$PWD:$PYTHONPATH"
          '';
        };

        # Helper app that installs the user unit
        apps.install-service = {
          type = "app";
          program = toString (pkgs.writeShellScript "install-lcd-display-service" ''
            set -euo pipefail
            UNIT_DIR="''${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
            mkdir -p "$UNIT_DIR"
            cat > "$UNIT_DIR/lcd-display.service" <<EOF
            [Unit]
            Description=LCD Display Manager (16x2)
            After=graphical-session.target
            PartOf=graphical-session.target

            [Service]
            ExecStart=${lcd-display}/bin/lcd-display --display vu
            Restart=on-failure
            RestartSec=3
            PassEnvironment=NIRI_SOCKET XDG_RUNTIME_DIR

            [Install]
            WantedBy=graphical-session.target
            EOF
            systemctl --user daemon-reload
            echo "Installed lcd-display.service"
            echo "  systemctl --user enable --now lcd-display.service"
            echo "  systemctl --user status lcd-display.service"
          '');
        };
      });
}