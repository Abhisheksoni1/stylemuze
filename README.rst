Install virtualenv via pip:
$ pip install virtualenv

Test your installation
$ virtualenv --version

Create a virtual environment for a project:
$ cd my_project_folder
$ virtualenv my_project

To begin using the virtual environment, it needs to be activated:
$ source my_project/bin/activate

Install packages as usual, for example:
$ pip install -r >requirements.txt

to runserver
./manage.py runserver YOURIP:8000

to run celery
open another terminal and then run this command along with server in virtualenv instance(another)
$ celery -A stylemuze worker -l info

