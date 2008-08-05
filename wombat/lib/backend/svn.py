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
from wombat.model import Revision, File
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
    rev_q = session.query(Revision).filter_by(id=rev_id)
    try:
        revision = rev_q.one()
    except InvalidRequestError:
        xml_string = call_svn_cmd(path, "log", "--incremental --xml -r %s" % rev_id)
        svn = parse_svn(xml_string)
        revision = Revision(svn.revision, u"r%s" % svn.revision, svn.msg, svn.author, svn.date)
        session.save(revision)

    return revision

def create_rev_entry(rev_path, session):
    """string, Session -> None
    Generate a database entry.
    """
    xml_string = call_svn_cmd(rev_path, "info", "--incremental --xml")
    svn = parse_svn(xml_string)
    revision = get_create_revision(rev_path, session, svn.revision)

    old_file = session.query(File).filter_by(path=unicode(rev_path)).first()
    if old_file is not None:
        session.delete(old_file)

    new_file = File(svn.path, os.path.basename(svn.path),
            os.path.getsize(svn.path), svn.root)
    new_file.revision = revision
    session.save(new_file)

def scan(session):
    """Session -> None
    Iterate over the media dir and generate database entries
    """
    media_dir = config['app_conf']['media_dir']
    cwd = os.getcwd()
    os.chdir(media_dir)
    for root, dirs, files in os.walk(media_dir):
        new_root = root.replace(media_dir,'').lstrip('/')
        for file in files:
            file_path = os.path.join(new_root, file)
            create_rev_entry(file_path, session)

        if ".svn" in dirs:
            dirs.remove(".svn")
    session.commit()
    os.chdir(cwd)

def delete_file_entry(rev_path, session):
    """string, Session -> None
    Delete a file entry
    """
    del_file = session.query(File).filter_by(path=rev_path).first()
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

    for action, path in svn.changed_paths:
        if action in (u'M', u'A'):
            create_rev_entry(path, session)
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

