# Copyright (C) 2008 by Kai Blin
#
# WOMBAT is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin St, Fifth Floor, Boston, MA 02110-1301, USA

import os
import os.path
from pylons import config
from wombat.model import Revision, File, Dir
from sqlalchemy.exceptions import InvalidRequestError
from svn_xml_parser import parse_svn

def call_svn_cmd(path, cmd, opts):
    """string, string, string -> string
    Call a svn command and return an xml string
    """
    stringlist = []
    cli_in, cli_out = os.popen2("svn %s %s '%s' 2> /dev/null" % (cmd, opts, path))
    cli_in.close()
    try:
        stringlist = cli_out.readlines()
        xml_string = "".join(stringlist)
        return xml_string
    finally:
        cli_out.close()

    return None

def get_create_revision(path, session, rev_id):
    """string, Session, int -> Revision
    Fetch revision with id 'rev_id' from database or create a new entry.
    """
    revision = session.query(Revision).get(rev_id)
    if revision is None:
        xml_string = call_svn_cmd(path, "log", "--incremental --xml -r %s" % rev_id)
        if xml_string == "":
            return None
        svn = parse_svn(xml_string)
        revision = Revision(svn.revision, u"r%s" % svn.revision, svn.msg, svn.author, svn.date)
        session.save(revision)

    return revision

def create_rev_entry(rev_path, rev_id, session):
    """string, Session -> None
    Generate a database entry.
    """
    if not os.path.exists(rev_path):
        return

    if rev_id > 0:
        xml_string = call_svn_cmd(rev_path, "info", "--incremental --xml -r %s" % rev_id)
    else:
        xml_string = call_svn_cmd(rev_path, "info", "--incremental --xml")

    svn = parse_svn(xml_string)
    revision = get_create_revision(rev_path, session, svn.revision)
    if revision is None:
        return

    if svn.kind == u"file":
        old_file = session.query(File).get(unicode(rev_path))
        if old_file is not None:
            old_file.size = os.path.getsize(rev_path)
            old_file.revision = revision
            parent = old_file.directory
            while parent is not None:
                parent.revision = revision
                session.update(parent)
                parent = parent.parent
            session.update(old_file)
            return

        new_file = File(rev_path, os.path.basename(rev_path),
                os.path.getsize(rev_path), svn.root)
        new_file.revision = revision
        session.save(new_file)

        parent_path = os.path.dirname(svn.path)
        if parent_path == u'':
            parent_path = u'.'
        parent_dir = session.query(Dir).get(parent_path)
        if parent_dir is not None:
            new_file.directory = parent_dir

        session.update(new_file)
    elif svn.kind == u"dir":
        old_dir = session.query(Dir).get(unicode(rev_path))
        if old_dir is not None:
            old_dir.revision = revision
            session.update(revision)
            return

        if svn.path != u'.':
            dir_name = os.path.basename(svn.path)
        else:
            dir_name = u'/'
        new_dir = Dir(svn.path, dir_name, svn.root)
        new_dir.revision = revision

        parent_path = os.path.dirname(svn.path)
        if parent_path == u'':
            parent_path = u'.'
        parent_dir = session.query(Dir).get(parent_path)
        if parent_dir is not None and svn.path != u'.':
            new_dir.parent = parent_dir
        session.save_or_update(new_dir)

def scan(session):
    """Session -> None
    Iterate over the media dir and generate database entries
    """
    media_dir = config['app_conf']['media_dir']
    cwd = os.getcwd()
    os.chdir(media_dir)
    for root, dirs, files in os.walk(media_dir):
        new_root = root.replace(media_dir,'').lstrip('/')
        create_rev_entry(new_root, session)
        for file in files:
            file_path = os.path.join(new_root, file)
            create_rev_entry(file_path, -1, session)

        if ".svn" in dirs:
            dirs.remove(".svn")
    session.commit()
    os.chdir(cwd)

def delete_file_entry(rev_path, session):
    """string, Session -> None
    Delete a file entry
    """
    del_file = session.query(File).get(rev_path)
    if del_file is not None:
        session.delete(del_file)

def update_rev(session, rev_id):
    """Session, int -> None
    Update a revision entry
    """
    xml_string = call_svn_cmd(".", "log", "--incremental --xml -v -r %s" % rev_id)
    svn = parse_svn(xml_string)
    revision = Revision(svn.revision, u"r%s" % svn.revision, svn.msg, svn.author, svn.date)
    session.save(revision)

    # reverse the order of the changed paths, as svn info --xml reverses them as
    # well. This way we don't add files before adding the parent dir.
    svn.changed_paths.reverse()

    for action, path in svn.changed_paths:
        if action in (u'M', u'A'):
            create_rev_entry(path, rev_id, session)
        elif action in (u'D'):
            delete_file_entry(path, session)
        else:
            continue

def update(session):
    """Session -> None
    Update to latest svn revision if needed
    """
    revision = session.query(Revision).max(Revision.id)
    cwd = os.getcwd()
    os.chdir(config['app_conf']['media_dir'])
    xml_string = call_svn_cmd(".", "info", "--incremental --xml")
    svn = parse_svn(xml_string)
    while revision < svn.revision:
        revision += 1
        update_rev(session, revision)
    session.commit()
    os.chdir(cwd)

