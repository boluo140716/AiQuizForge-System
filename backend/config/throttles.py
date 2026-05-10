from rest_framework.throttling import SimpleRateThrottle

#生成基于用户id的测验限流器
class GenerateQuizRateThrottle(SimpleRateThrottle):

    scope = 'generate_quiz'
    #根据用户id作为缓存键,未登录用户用ip地址限制
    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            ident=request.user.pk
        else:
            ident=self.get_ident(request)    #获取ip地址
        return self.cache_format % {         #缓存键格式
            'scope': self.scope,
            'ident': ident,     
        }
