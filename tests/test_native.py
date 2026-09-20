import copy
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import system_info as si
import native_backend as nb

class Detection(unittest.TestCase):
    def test_native_family_wins_over_other_installed_managers(self):
        for distro,manager in [('debian','apt'),('arch','pacman'),('gentoo','portage'),('fedora','dnf'),('opensuse-tumbleweed','zypper')]:
            self.assertEqual(si.detect({'ID':distro},lambda c:'/usr/bin/'+c)['manager'],manager)
    def test_derivative(self):
        self.assertEqual(si.detect({'ID':'custom','ID_LIKE':'arch'},lambda c:c)['manager'],'pacman')
    def test_missing_native_does_not_fall_back(self):
        with self.assertRaises(RuntimeError):si.detect({'ID':'debian'},lambda c:None if c=='apt-get' else c)
    def test_unknown_fails_closed(self):
        with self.assertRaises(RuntimeError):si.detect({'ID':'unknown'},lambda c:c)

class Plans(unittest.TestCase):
    def setUp(self):
        self.system=dict(manager='pacman',distro='arch',release='rolling',arch='x86_64',command='/usr/bin/pacman')
        self.rows={k:nb.row(k,'2') for k in ['base','app','new-update-lib','extra','extra-lib']}
        self.rows['base']['protected']=True
        self.rows['app']['deps']=['new-update-lib']
        self.rows['extra']['deps']=['extra-lib']
        self.rows['extra-lib']['manual']=False
    def point(self):
        return dict(format=2,system=si.identity(self.system),packages={'base':'1','app':'1','missing':'1'})
    def test_point_keeps_updated_package_and_new_dependencies(self):
        plan=nb.plan_for(dict(mode='point',point=self.point()),self.system,self.rows)
        self.assertEqual(plan['removed'],['extra','extra-lib'])
        self.assertEqual(plan['missing'],['missing'])
    def test_cannot_remove_protected(self):
        with self.assertRaises(RuntimeError):nb.plan_for(dict(mode='remove',selected=['base']),self.system,self.rows)
    def test_reject_required_package(self):
        with self.assertRaises(RuntimeError):nb.plan_for(dict(mode='remove',selected=['new-update-lib']),self.system,self.rows)
    def test_remove_dependency_only_if_unused(self):
        req=dict(mode='remove',selected=['extra'],dependencies=True)
        self.assertEqual(nb.plan_for(req,self.system,self.rows)['removed'],['extra','extra-lib'])
        self.rows['app']['deps'].append('extra-lib')
        self.assertEqual(nb.plan_for(req,self.system,self.rows)['removed'],['extra'])
    def test_cross_manager_point_rejected(self):
        point=self.point();point['system']['manager']='dnf'
        with self.assertRaises(RuntimeError):nb.plan_for(dict(mode='point',point=point),self.system,self.rows)
    def test_metadata_ui_does_not_change_authorization_hash(self):
        req=dict(mode='remove',selected=['extra'])
        before=nb.plan_for(req,self.system,self.rows)['hash']
        self.rows['app']['title']='Localized title';self.rows['app']['icon']='other'
        self.assertEqual(before,nb.plan_for(req,self.system,self.rows)['hash'])
        self.rows['app']['version']='3'
        self.assertNotEqual(before,nb.plan_for(req,self.system,self.rows)['hash'])
    def test_bad_target_rejected(self):
        for target in ['--nodeps','x; rm -rf /','$(id)','foo\nbar']:
            with self.assertRaises(RuntimeError):nb.command(self.system,[target])
    def test_commands_never_skip_dependency_checks_or_auto_confirm(self):
        for manager,package in [('pacman','app'),('dnf','app.x86_64'),('zypper','app.x86_64'),('portage','app-misc/app:0')]:
            system=self.system|dict(manager=manager,command=manager)
            command=nb.command(system,[package])
            for bad in ['--nodeps','--unmerge','--noconfirm','--assumeyes','-y','--force']:
                self.assertNotIn(bad,command)
            self.assertIn(package,command)
    def test_stale_plan_never_executes_removal(self):
        req=dict(mode='remove',selected=['extra'])
        with patch.object(nb.os,'geteuid',return_value=0), patch.object(nb,'snapshot',return_value=self.rows), patch.object(nb.subprocess,'run') as execute:
            with self.assertRaises(RuntimeError):nb.apply(dict(request=req,hash='stale'),self.system)
            execute.assert_not_called()
    def test_apply_requires_admin(self):
        with patch.object(nb.os,'geteuid',return_value=1000):
            with self.assertRaises(RuntimeError):nb.apply({},self.system)
    def test_pacman_desc_parser(self):
        self.assertEqual(nb.pacman_fields('%NAME%\napp\n\n%DEPENDS%\nlib>=2\nother\n\n'),{'NAME':['app'],'DEPENDS':['lib>=2','other']})
    def test_rpm_provider_graph(self):
        records=[]
        for fields in [('app','x86_64','2','30','Application','lib(foo)\n','app\n','/usr/bin/app\n'),('lib','x86_64','3','50','Library','','lib(foo)\n','/usr/lib/foo\n')]:
            records.append('\x1f'.join(fields)+'\x1e')
        with patch.object(nb,'run',return_value=''.join(records)):
            rows=nb.rpm_inventory(dict(manager='dnf'))
        self.assertEqual(rows['app.x86_64']['deps'],['lib.x86_64'])

if __name__=='__main__':unittest.main()
