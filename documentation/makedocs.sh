sphinx-apidoc -f -M --separate -o apidoc ../wntr
pushd apidoc
for file in *.rst
do
    sed -e 's/:undoc-members:/:no-undoc-members:/' $file > tmp.txt
    mv tmp.txt $file
done
popd
make html
