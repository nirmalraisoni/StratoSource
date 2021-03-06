#    Copyright 2010, 2011 Red Hat Inc.
#
#    This file is part of StratoSource.
#
#    StratoSource is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    StratoSource is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with StratoSource.  If not, see <http://www.gnu.org/licenses/>.
#    
from django.db import models
from django.db.models.signals import pre_save
from django.core.exceptions import ObjectDoesNotExist
from django.dispatch import receiver
import datetime
import logging



class ConfigSetting(models.Model):
    key             = models.CharField(max_length=250, blank=False, null=False, unique=True)
    value           = models.CharField(max_length=1000, blank=True, null=True)
    type            = models.CharField(max_length=20, default='text')
    allow_delete    = models.BooleanField(default=True)
    masked          = models.BooleanField(default=False)
  
#class UserDetails(models.Model):
#    USER_TYPES = (('dev','Developer'),('bua','Business Analyst'),('evm','Environment Manager'),('unk','Unknown'))
#    user =      models.OneToOneField('User')
#    user_type = models.CharField(max_length=3, choices=USER_TYPES, default='unk')

class AdminMessage(models.Model):
    to        = models.CharField(max_length=50, default='any')
    sender    = models.CharField(max_length=50, default='unknown')
    subject   = models.CharField(max_length=100)
    body      = models.CharField(max_length=255)
    event_time= models.DateField(default=datetime.datetime.now)
    handled_by= models.CharField(max_length=100)

    def __unicode__(self):
        return self.subject + ' - ' + str(self.event_time)

class Repo(models.Model):
    name =      models.CharField(max_length=20)
    location =  models.CharField(max_length=255)


    def __unicode__(self):
        return self.name + " - " + self.location

class Branch(models.Model):
    CRONFREQ = (
        ('h', 'Hourly'), ('d', 'Daily'),
    )

    RUNSTATUS = (
        ('u', 'Unknown'), ('r', 'Running'), ('d', 'Done'),  ('e', 'Error'),
    )

    repo =  models.ForeignKey(Repo)
    name =  models.CharField(max_length=30)
    api_env =   models.CharField(max_length=10, default='test')     # "test" or "login"
    api_pod =   models.CharField(max_length=10, default='cs4')
    api_user =  models.CharField(max_length=100)
    api_pass =  models.CharField(max_length=100, blank=True, null=True)
    api_auth =  models.CharField(max_length=50, blank=True, null=True)
    api_store = models.CharField(max_length=100, default='/tmp')
    api_assets= models.CharField(max_length=500,
        default='EntitlementTemplate,HomePageComponent,ArticleType,ApexPage,ApexClass,ApexTrigger,ApexComponent,'+
                'CustomPageWebLink,CustomLabels,CustomApplication,CustomObject,CustomObjectTranslation,Translations,'+
                'CustomSite,CustomTab,DataCategoryGroup,HomePageLayout,Layout,Portal,Profile,RecordType,'+
                'RemoteSiteSetting,ReportType,Scontrol,StaticResource,Workflow')
    enabled = models.BooleanField(default=True)
    cron_enabled = models.BooleanField(default=True)
    cron_type = models.CharField(max_length=1, choices=CRONFREQ,default='h')
    run_status = models.CharField(max_length=1, choices=RUNSTATUS,default='u', blank=True, null=True)
    cron_interval = models.IntegerField(default=1)
    cron_start = models.CharField(max_length=5, default='0')

    def __unicode__(self):
        return self.repo.name + " - " + self.name    

class BranchLog(models.Model):
    lastlog = models.CharField(max_length=20000)
    branch =  models.ForeignKey(Branch)

class Story(models.Model):
    rally_id =          models.CharField(max_length=20,blank=True,null=True)
    sprint =            models.CharField(max_length=255)
    name =              models.CharField(max_length=255)
    url =               models.CharField(max_length=1024,blank=True,null=True)
    release_date =      models.DateField(blank=True,null=True)
    released =          models.BooleanField(default=False)
    done_on_branches =  models.ManyToManyField(Branch,null=True)

    def __unicode__(self):
        return self.name + " " + self.rally_id
        
class Commit(models.Model):
    STATUS_TYPES = (('p','Pending Analysis'),('c','Complete'))

    branch =        models.ForeignKey(Branch)
    hash =          models.CharField(max_length=100, db_index=True)
    prev_hash =     models.CharField(max_length=100)
    comment =       models.CharField(max_length=200,blank=True,null=True)
    date_added =    models.DateTimeField(default=datetime.datetime.now)
    status =        models.CharField(max_length=1, choices=STATUS_TYPES, default='p')
    parser_ver =    models.CharField(max_length=2, default='01')    # future-proofing SF changes to XML schema

    def __unicode__(self):
        return self.branch.name + " - " + self.hash + " - " + self.comment

class Release(models.Model):
    name =              models.CharField(max_length=255)
    release_notes =     models.CharField(max_length=4000)
    est_release_date =  models.DateField(blank=True,null=True)
    release_date =      models.DateField(blank=True,null=True)
    released =          models.BooleanField(default=False)
    hidden =            models.BooleanField(default=False)
    stories =           models.ManyToManyField(Story,null=True)

    def __unicode__(self):
        return self.name
    
class DeployableObject(models.Model):
    STATUS_TYPES = (('a','Active'),('d','Deleted'))
    RELEASE_STATUS = (('r','Released'),('c','Changed'),('p','Pending Release'),('e','Conflicting'))

    pending_stories =   models.ManyToManyField(Story,null=True,related_name='%(app_label)s_%(class)s_pending')
    released_stories =  models.ManyToManyField(Story,null=True,related_name='%(app_label)s_%(class)s_released')

    filename =          models.CharField(max_length=200, db_index=True)
    type =              models.CharField(max_length=20, db_index=True)
    el_type =           models.CharField(max_length=20,blank=True,null=True)
    el_subtype =        models.CharField(max_length=20,blank=True,null=True)
    el_name =           models.CharField(max_length=100,blank=True,null=True)
    status =            models.CharField(max_length=1, choices=STATUS_TYPES, default='a')
    release_status =    models.CharField(max_length=1, choices=RELEASE_STATUS, default='r')
    branch =            models.ForeignKey(Branch, db_index=True)

    def __unicode__(self):
        s = self.branch.name + " - " + self.type + " - " + self.filename + " - " + self.status
        if not self.el_type is None: s = s + " - " + self.el_type
        if not self.el_name is None: s = s + " - " + self.el_name
        return s 

class DeploymentPackage(models.Model):
    name =               models.CharField(max_length=1000)
    release =            models.ForeignKey(Release, db_index=True)
    date_added =         models.DateTimeField(default=datetime.datetime.now)
    last_pushed =        models.DateTimeField(null=True)
    source_environment = models.ForeignKey(Branch, null=False, related_name='to_deployment_packages')
    deployable_objects = models.ManyToManyField(DeployableObject,null=True)

class DeploymentPushStatus(models.Model):
    RESULT_TYPES = (('n','New'),('i','In Progress'),('s','Successful'),('f','Failed'))

    package =            models.ForeignKey(DeploymentPackage)
    date_attempted =     models.DateField(default=datetime.datetime.now)
    log_output =         models.CharField(max_length=20000)
    result =             models.CharField(max_length=1, choices=RESULT_TYPES, default='n')
    test_only =          models.BooleanField(default=True)
    keep_package =       models.BooleanField(default=False)
    target_environment = models.ForeignKey(Branch, null=False, related_name='from_deployment_packages')
    package_location =   models.CharField(max_length=200, null=True)

class SalesforceUser(models.Model):
    userid      = models.CharField(max_length=20, blank=False, null=False)
    name        = models.CharField(max_length=100, blank=False, null=False, db_index=True)
    email       = models.CharField(max_length=100, blank=False, null=False)

class ReleaseTask(models.Model):
    name =           models.CharField(max_length=1000)
    done_in_branch = models.CharField(max_length=100)
    order =          models.IntegerField(default=0)
    user =           models.ForeignKey(SalesforceUser, blank=True, null=True, db_index=True)  
    release =        models.ForeignKey(Release, blank=True, null=True, db_index=True)
    story =          models.ForeignKey(Story, blank=True, null=True, db_index=True)
    
class UserChange(models.Model):
    branch =    models.ForeignKey(Branch, db_index=True)
    apex_id   = models.CharField(max_length=20, blank=True, null=True, unique=False)
    apex_name = models.CharField(max_length=200, blank=False, null=False, unique=False, db_index=True)
    sfuser =    models.ForeignKey(SalesforceUser, db_index=True)
    batch_time = models.DateTimeField()
    last_update = models.DateTimeField()
    object_type = models.CharField(max_length=20, blank=False, null=False)

class Delta(models.Model):
    DELTA_TYPES = (('a','Add'),('d','Delete'),('u','Update'))

    object =        models.ForeignKey(DeployableObject)
    commit =        models.ForeignKey(Commit)
    delta_type =    models.CharField(max_length=1,choices=DELTA_TYPES)
    user_change =   models.ForeignKey(UserChange, blank=True, null=True)

    def __unicode__(self):
        return self.object.__unicode__() + " - " + self.delta_type

    def getDeltaType(self):
        if self.delta_type == 'a': return 'Add'
        if self.delta_type == 'd': return 'Delete'
        if self.delta_type == 'u': return 'Update'

class DeployableTranslation(models.Model):
    STATUS_TYPES = (('a','Active'),('d','Deleted'))
    RELEASE_STATUS = (('r','Released'),('c','Changed'),('p','Pending Release'),('e','Conflicting'))

    pending_stories =   models.ManyToManyField(Story,null=True,related_name='%(app_label)s_%(class)s_pending')
    released_stories =  models.ManyToManyField(Story,null=True,related_name='%(app_label)s_%(class)s_released')

    label =             models.CharField(max_length=200)
    locale =            models.CharField(max_length=10)
    status =            models.CharField(max_length=1, choices=STATUS_TYPES, default='a')
    release_status =    models.CharField(max_length=1, choices=RELEASE_STATUS, default='r')
    branch =            models.ForeignKey(Branch, db_index=True)

    def __unicode__(self):
        s = self.branch.name + " - " + self.label + " - " + self.locale
        return s

class TranslationDelta(models.Model):

    translation =   models.ForeignKey(DeployableTranslation)
    commit =        models.ForeignKey(Commit)
    delta_type =    models.CharField(max_length=1,choices=Delta.DELTA_TYPES)

    def __unicode__(self):
        return self.translation.locale + " - " + self.translation.label + " - " + self.delta_type

    def getDeltaType(self):
        if self.delta_type == 'a': return 'Add'
        if self.delta_type == 'd': return 'Delete'
        if self.delta_type == 'u': return 'Update'


class UnitTestBatch(models.Model):
    batch_time      = models.DateTimeField(default=datetime.datetime.now, db_index=True)
    branch          = models.ForeignKey(Branch)
    tests           = models.IntegerField(default=0)
    failures        = models.IntegerField(default=0)
    runtime         = models.IntegerField(default=0)

class UnitTestRun(models.Model):
    apex_class_id   = models.CharField(max_length=20, blank=False, null=False, unique=False)
    batch           = models.ForeignKey(UnitTestBatch)
    class_name      = models.CharField(max_length=200, blank=False, null=False)
    branch          = models.ForeignKey(Branch)
    tests           = models.IntegerField(default=0)
    failures        = models.IntegerField(default=0)
    runtime         = models.IntegerField(default=0)

class UnitTestRunResult(models.Model):
    test_run =  models.ForeignKey(UnitTestRun)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    method_name = models.CharField(max_length=200)
    outcome = models.CharField(max_length=50)
    message = models.CharField(max_length=255, blank=True, null=True)
    runtime = models.IntegerField(default=0)

class UnitTestSchedule(models.Model):
    CRONFREQ = (
        ('h', 'Hourly'), ('d', 'Daily'), ('w', 'Weeky'),        
    )
    
    branch =  models.ForeignKey(Branch)
    results_email_address = models.CharField(max_length=500)
    email_only_failures = models.BooleanField(default=True)
    cron_enabled = models.BooleanField(default=True)
    cron_type = models.CharField(max_length=1, choices=CRONFREQ,default='d')
    cron_interval = models.IntegerField(default=1)
    cron_start = models.CharField(max_length=5, default='0')



###
# model signals
###

@receiver(pre_save, sender=Delta)
def Delta_pre_save(sender, **kwargs):
    row = kwargs['instance']

    #
    # On insert, detect conflicts
    #
    depobj = row.object
    if depobj.release_status == 'r':
        depobj.release_status = 'c'
    elif depobj.release_status == 'p':
        depobj.release_status = 'e'
    else:
        depobj.release_status = 'c'

    depobj.save()

    #
    # Handle delete deltas by flagging the deployable object as deleted.
    #
    if row.delta_type == 'd':
        depobj.status = 'd'
        depobj.save()

@receiver(pre_save, sender=TranslationDelta)
def TranslationDelta_pre_save(sender, **kwargs):
    row = kwargs['instance']

    trans = row.translation
    if trans.release_status == 'r':
        trans.release_status = 'c'
    elif trans.release_status == 'p':
        trans.release_status = 'e'
    else:
        trans.release_status = 'c'
    trans.save()

    #
    # Handle delete deltas by flagging the deployable object as deleted.
    #
    if row.delta_type == 'd':
        trans.status = 'd'
        trans.save()



@receiver(pre_save, sender=DeployableObject)
def DeployableObject_pre_save(sender, **kwargs):
    row = kwargs['instance']

    depobj = row
    # if with this update there are no pending stories, but the object is not in a released state
    # move it back to "changed" from error, or pending state.
    if depobj.id != None:
        if len(depobj.pending_stories.all()) == 0 and depobj.release_status != 'r':
            depobj.release_status = 'c'
        
@receiver(pre_save, sender=DeployableTranslation)
def DeployableTranslation_pre_save(sender, **kwargs):
    row = kwargs['instance']

    trans = row
    # if with this update there are no pending stories, but the object is not in a released state
    # move it back to "changed" from error, or pending state.
    if trans.id != None:
        if len(trans.pending_stories.all()) == 0 and trans.release_status != 'r':
            trans.release_status = 'c'
