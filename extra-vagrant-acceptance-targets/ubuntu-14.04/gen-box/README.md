```
vagrant up node1
vagrant ssh node1
```
log in and run flocker-deploy --version, run `pip install` until all the deps are met :(
```
vagrant package node1
```
Then upload `package.box` to Atlas.
