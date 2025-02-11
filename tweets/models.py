from django.db import models
from django.contrib.auth.models import User
from utils.time_helpers import utc_now
from django.contrib.contenttypes.models import ContentType
from likes.models import Like
from tweets.constants import TweetPhotoStatus, TWEET_PHOTO_STATUS_CHOICES

# https://stackoverflow.com/questions/35129697/difference-between-model-fieldsin-django-and-serializer-fieldsin-django-rest
# Create your models here.
class Tweet(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        help_text="This user refers to the user who posts this tweet.",
        verbose_name=u"谁发了这个帖子",
    )
    content = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True) # 有时区（vagrant/server所在的时区）

    # Meta是一个配置信息。
    # 在创建Tweets这个model的时候会根据配置信息去创建。
    class Meta:
        # 联合索引 compound index/composite index
        # 相当于在数据库中建立了一个我看不到的表单，这个表单中一共有3列。
        # [
        #   ('user', 'created_at', 'id'),
        #   ...
        # ]

        # 建立了索引也要进行makemigration和migrate
        index_together = (
            ('user', 'created_at'),
        )

        # 在Tweet相关的所有queryset中如果没有指定orderby的时候，默认的是下面这个ordering。
        # 即，只会影响orderby的默认排序行为。
        # ordering 不会对数据库产生影响。
        ordering = ('user', '-created_at')



    @property
    def hours_to_now(self):
        # datetime.now()不带时区信息，需要增加上utc的时区信息。
        return (utc_now()-self.created_at).seconds // 3600

    def __str__(self):
        # 当执行 print(tweet instance) 的时候会显示的内容
        return f'{self.created_at} {self.user}: {self.content}'

    @property
    def like_set(self):
        # 找到tweet下所有的点赞。
        return Like.objects.filter(
            content_type=ContentType.objects.get_for_model(Tweet),
            object_id=self.id,
        ).order_by('-created_at')


class TweetPhoto(models.Model):
    # 图片在哪个 Tweet 下面
    tweet = models.ForeignKey(Tweet, on_delete=models.SET_NULL, null=True)

    # 谁上传了这张图片，这个信息虽然可以从 tweet 中获取到，但是重复的记录在 Image 里可以在
    # 使用上带来很多遍历，比如某个人经常上传一些不合法的照片，那么这个人新上传的照片可以被标记
    # 为重点审查对象。或者我们需要封禁某个用户上传的所有照片的时候，就可以通过这个 model 快速
    # 进行筛选
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)

    # 图片文件
    file = models.FileField()
    order = models.IntegerField(default=0)

    # 图片状态，用于审核等情况
    status = models.IntegerField(
        default=TweetPhotoStatus.PENDING,
        choices=TWEET_PHOTO_STATUS_CHOICES,
    )

    # 软删除(soft delete)标记，当一个照片被删除的时候，首先会被标记为已经被删除，在一定时间之后
    # 才会被真正的删除。这样做的目的是，如果在 tweet 被删除的时候马上执行真删除的通常会花费一定的
    # 时间，影响效率。可以用异步任务在后台慢慢做真删除。
    has_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        index_together = (
            ('user', 'created_at'),
            ('has_deleted', 'created_at'),
            ('status', 'created_at'),
            ('tweet', 'order'),
        )

    def __str__(self):
        return f'{self.tweet_id}: {self.file}'
