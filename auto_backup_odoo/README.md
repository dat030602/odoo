# BACKUP ODOO DATABASES & FILESTORE

**Available Odoo Backup DB/Filestore Modes:**

* **Local**
* **Remote Server**
* **Google Drive**
* **Dropbox**
* **Amazon S3**

**Module For backup ODOO databases and automating the backup process of ODOO.**

* Multiple Backup Modes
* **Filestore** Backup
* Backup **ODOO Databases** in specified path
* Detailed Message Log
* Backup Status Information and History
* User can select the format to dump, either custom archive, plain text SQL or tar archive
* Archive Backup Process
* Repeat Missed Backup Process

# Features

* Dump ODOO Database in specified format
* Zip filestore in a specified loaction
* Output a custom archive suitable for input into pg_restore. This is the most flexible format in that it allows the reordering of loading data as well as to object definitions. This format is also compressed by default. Here we user gzip ie, test.gz, We also recommend you to select Custom, because Using the custom format you can restore single objects from a backup.
* Output a plain-text SQL script file (the default). The plain text format is useful for very small databases with a minimal number of objects but other than that, it should be avoided.
* Output a tar archive suitable for input into pg_restore. Using this archive format allows reordering and/or exclusion of database objects at the time the database is restored. It is also possible to limit which data is reloaded at restore time. we use tar with gzip
* Backup Filestore
* Multiple backup modes at sametime

### Tech

Odoo Auto Backup Module uses

* [PYTHON](https://www.python.org/) - Models
* [XML](https://www.w3.org/XML/) - Views
* [HTML](https://www.w3.org/html/) - UI
* [Twitter Bootstrap](https://getbootstrap.com/2.3.2/) - UI
* [backbone.js](http://backbonejs.org/) - Views
* [jQuery](https://jquery.com/)
* [PSQL](https://www.postgresql.org/) - DB

### External Dependencies
`pip depends on your python version / mapped pip version.`
* [PYSFTP](https://pypi.org/project/pysftp/) `pip install pysftp`
* [Dropbox](https://pypi.org/project/dropbox/) `pip install dropbox`
* [Progress Meter](https://pypi.org/project/tqdm/) `pip install tqdm`
* [Boto3](https://pypi.org/project/boto3/) `pip install boto3`
* [Botocore](https://pypi.org/project/botocore/) `pip install botocore`
* [Simplejson](https://pypi.org/project/simplejson/) `pip install simplejson`

### Installation

Install the odoo and Auto Backup module. After installation you can configure backup under general settings. If you are using the google drive mode, then msust enable the google integration under general settings and update the google drive refresh token.

### CHANGELOGS
>Date: 07/12/2020
* Performance Improvement
* Session Upload Trace For Dropbox Files > 150 mb
* Full Metadata Track In Message Logs
* Fix Dropbox Tar files upload
* Progress Meter In Logs
>Date: 22/11/2020
* Amazon S3 Database Backup
* Amazon S3 Filestore Backup

### Todos

* Backup Dashboard

### Author

[Hilar AK](https://www.linkedin.com/in/hilar-ak/) `https://www.linkedin.com/in/hilar-ak/`

### Git Repository

[Hilar AK](https://github.com/hilarak) `hilarak@gmail.com`
