# Generated by Django 2.2.27 on 2022-04-09 14:11

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone

import logging
logger = logging.getLogger(__name__)

def forwards_func(apps, schema_editor):
    """
        This migration changes the way an ActivitySlot is linked to an activity. Instead of
        linking to an Activity directly through a recurrence_id, it now instead links to an ActivityMoment.

        To migrate all old references, we need to:
        1) Find a matching ActivityMoment with an identical parent_activity and recurrence_id
        2) Create a new ActivityMoment if such an ActivityMoment does not exist yet
    """
    ActivityMoment = apps.get_model("activity_calendar", "ActivityMoment")
    ActivitySlot = apps.get_model("activity_calendar", "ActivitySlot")

    for slot in ActivitySlot.objects.all():
        if slot.recurrence_id is None:
            # There are some activityslots left from an ancient past where a recurrence_id was
            #   not defined for non-recurring activities. These slots are currently invisible
            #   in Squire, so let's fix those while we're at it.
            logger.warning(f"Found a faulty ActivitySlot ({slot.id}) without a recurrence_id. Using the start_date ({slot.parent_activity.start_date}) of its parent_activity instead.")
            slot.recurrence_id = slot.parent_activity.start_date

        moment, is_new = ActivityMoment.objects.get_or_create(parent_activity=slot.parent_activity, recurrence_id=slot.recurrence_id)
        if is_new:
            logger.warning(f"Could not find a matching ActivityMoment for slot {slot.id}', so a new one was created instead ({moment.id}).\n\tSlot title: {slot.title}.\n\tActivity title ({slot.parent_activity_id}): {slot.parent_activity.title}")
        slot.parent_activitymoment = moment
        slot.save()

def backwards_func(apps, schema_editor):
    """
        The reverse of the previous function. ActivitySlots should regain their recurrence_id.
        NB: This is not a 1-to-1 reversion:
        1) ActivitySlots that used to have no recurrence_id will keep their new recurrence_id. Not only is there no way to
            know which ActivitySlot used to work like this, they're also not visible in the current version of Squire.
        2) Newly created ActivityMoments are not removed. It would technically be possible to get rid of non-cancelled
            ActivityMoments that do not feature changes from their parent activity and which also fall in their parent's
            recurrence scheme, but there's no real benefit there. Furthermore, this could also remove ActivityMoments
            that match those requirements but were also there prior to this migration (though removing those wouldn't hurt
            either).
    """
    ActivitySlot = apps.get_model("activity_calendar", "ActivitySlot")

    for slot in ActivitySlot.objects.all():
        slot.parent_activity = slot.parent_activitymoment.parent_activity
        slot.recurrence_id = slot.parent_activitymoment.recurrence_id
        slot.save()

class Migration(migrations.Migration):

    dependencies = [
        ('activity_calendar', '0022_activity_display_end_time'),
    ]

    operations = [
        migrations.AddField(
            model_name='activityslot',
            name='parent_activitymoment',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, related_name='activity_slot_set', to='activity_calendar.ActivityMoment', null=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='activityslot',
            name='parent_activity',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='activity_slot_set', to='activity_calendar.Activity', blank=True, null=True),
        ),
        migrations.RunPython(forwards_func, backwards_func),
        migrations.RemoveField(
            model_name='activityslot',
            name='parent_activity',
        ),
        migrations.RemoveField(
            model_name='activityslot',
            name='recurrence_id',
        ),
        migrations.AlterField(
            model_name='activityslot',
            name='parent_activitymoment',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='activity_slot_set', to='activity_calendar.ActivityMoment')
        ),
    ]
