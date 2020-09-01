#!/usr/bin/bash
#!/usr/bin/zsh

###### The file contains useful functions which can be added to `.bashrc` or `.zshrc` file.

### Obtain the absolute path of specified files or folders.
function ppf() {
    back=$(pwd -P)
    if [ $# -eq 0 ]; then
        /bin/ls . |sed "s:^:${back%/}/:" |sed 's/\([[:space:]]\)/\\\1/g' |sed '/\\$/d'
        return
    fi
    for f in $@; do
        if [ ! -e $f ]; then
            echo "\'$f\' doesn't exists."
            continue
        fi
        if [ -d $f ]; then
            cd "$f"
            arg=$(pwd -P)
            /bin/ls . |sed "s:^:${arg%/}/:" |sed 's/\([[:space:]]\)/\\\1/g' |sed '/\\$/d'
            cd "$back"
        else
            echo "${back}/$f"
        fi
    done
    return
}

### Use command line to open multiple pdf file. For MacOS, just use "preview" command.
### For Manjaro-Gnome, users can also use "xdg-open" to achieve this function, if change the system-wide default application for PDF files.
pdfTool=okular
function pdf(){
    if [ $# -eq 0 ]; then
        echo "No File Name"
    else
        for f in $@; do
            if [ ! -e $f ]; then
                echo "\'$f\' doesn't exists."
                continue
            fi
            $pdfTool $f &>/dev/null &
        done
    fi
    return
}

