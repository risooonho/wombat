from pylons import config
from sqlalchemy import Column, MetaData, Table, types, schema, ForeignKey
from sqlalchemy.orm import mapper, relation, backref
from sqlalchemy.orm import scoped_session, sessionmaker

Session = scoped_session(sessionmaker(bind=config['pylons.g'].sa_engine))

metadata = MetaData()

from revision import Revision, init_rev_table
rev_table = init_rev_table(metadata)

from file import File, init_files_table
files_table = init_files_table(metadata)

from dir import Dir, init_dirs_table
dirs_table = init_dirs_table(metadata)

from asset import Asset, init_assets_table
assets_table = init_assets_table(metadata)

from collection import Collection, init_collections_table
collections_table = init_collections_table(metadata)

from user import User, init_users_table
users_table = init_users_table(metadata)

from user_data import UserData, init_user_data_table
user_data_table = init_user_data_table(metadata)

from role import Role, init_roles_table
roles_table = init_roles_table(metadata)

from tag import Tag, init_tags_table
tags_table = init_tags_table(metadata)

user_roles = Table('user_roles', metadata,
        Column('user_id', types.Integer, ForeignKey('users.id')),
        Column('role_id', types.Integer, ForeignKey('roles.id'))
        )

asset_tags = Table('asset_tags', metadata,
        Column('asset_id', types.Integer, ForeignKey('assets.id')),
        Column('tag_id', types.Integer, ForeignKey('tags.id'))
        )

collection_tags = Table('collection_tags', metadata,
        Column('collection_id', types.Integer, ForeignKey('collections.id')),
        Column('tag_id', types.Integer, ForeignKey('tags.id'))
        )

files_queues = Table('files_queues', metadata,
        Column('file_path', types.Unicode(255), ForeignKey('files.path')),
        Column('queue_id', types.Integer, ForeignKey('download_queues.id'))
        )

from reset_data import ResetData, init_reset_data_table
reset_data_table = init_reset_data_table(metadata)

from email_confirm import EmailConfirm, init_email_confirm_table
email_confirm_table = init_email_confirm_table(metadata)

from download_queue import DownloadQueue, init_download_queue_table
download_queue_table = init_download_queue_table(metadata)

mapper(File, files_table)
mapper(Dir, dirs_table, properties={
    "files":relation(File, backref="directory"),
    "subdirs":relation(Dir, backref=backref("parent", remote_side=[dirs_table.c.path]))})
mapper(Revision, rev_table, properties={
    "files":relation(File, backref="revision"),
    "dirs":relation(Dir, backref="revision")})
mapper(Asset, assets_table, properties={
    "files":relation(File, backref="asset")})
mapper(Collection, collections_table, properties={
    "assets":relation(Asset, backref="collection")})
mapper(User, users_table)
mapper(UserData, user_data_table, properties={
    "user":relation(User, backref=backref("user_data", uselist=False),
                    single_parent=True, cascade="all, delete, delete-orphan")})
mapper(Role, roles_table, properties={
    "users":relation(User, secondary=user_roles, backref="roles",
                    cascade="all, delete")})
mapper(Tag, tags_table, properties={
    "assets":relation(Asset, secondary=asset_tags, backref="tags",
                    cascade="all, delete"),
    "collections":relation(Collection, secondary=collection_tags, backref="tags",
                    cascade="all, delete")})
mapper(ResetData, reset_data_table)
mapper(EmailConfirm, email_confirm_table)
mapper(DownloadQueue, download_queue_table, properties={
    "user":relation(User, backref=backref("download_queue", uselist=False),
                    single_parent=True, cascade="all, delete, delete-orphan"),
    "files":relation(File, secondary=files_queues, backref="in_queues")})


