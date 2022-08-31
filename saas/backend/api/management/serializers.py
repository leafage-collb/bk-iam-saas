# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-权限中心(BlueKing-IAM) available.
Copyright (C) 2017-2021 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from django.conf import settings
from django.utils.translation import gettext as _
from rest_framework import serializers

from backend.apps.application.serializers import ExpiredAtSLZ, ReasonSLZ
from backend.apps.role.serializers import RatingMangerBaseInfoSZL, RoleScopeSubjectSLZ
from backend.biz.role import RoleCheckBiz
from backend.service.constants import GroupMemberType, SubjectType
from backend.service.models import Subject


class ManagementSourceSystemSLZ(serializers.Serializer):
    system = serializers.CharField(label="调用API的系统id", max_length=32, help_text="用于认证是哪个系统调用了API")


class ManagementActionSLZ(serializers.Serializer):
    id = serializers.CharField(label="操作ID")


class ManagementResourcePathNodeSLZ(serializers.Serializer):
    system = serializers.CharField(label="系统ID")
    type = serializers.CharField(label="资源类型")
    id = serializers.CharField(label="资源实例ID", max_length=settings.MAX_LENGTH_OF_RESOURCE_ID)
    name = serializers.CharField(
        label="资源实例ID名称", allow_blank=True, trim_whitespace=False
    )  # 路径节点存在无限制，当id="*"则name可以为空


class ManagementResourcePathsSLZ(serializers.Serializer):
    system = serializers.CharField(label="系统ID")
    type = serializers.CharField(label="资源类型")
    paths = serializers.ListField(
        label="批量层级",
        child=serializers.ListField(label="拓扑层级", child=ManagementResourcePathNodeSLZ(label="实例"), allow_empty=False),
        allow_empty=True,
    )


class ManagementRoleScopeAuthorizationSLZ(serializers.Serializer):
    system = serializers.CharField(label="授权的系统id", max_length=32)
    actions = serializers.ListField(label="操作", child=ManagementActionSLZ(label="操作"), allow_empty=False)
    resources = serializers.ListField(
        # 如果action是与资源实例无关的，那么resources允许为空列表，但是字段还是要有，保持格式一致
        label="资源拓扑",
        child=ManagementResourcePathsSLZ(label="匹配资源拓扑"),
        allow_empty=True,
    )


class ManagementGradeManagerCreateSLZ(ManagementSourceSystemSLZ, RatingMangerBaseInfoSZL):
    authorization_scopes = serializers.ListField(
        label="可授权的权限范围", child=ManagementRoleScopeAuthorizationSLZ(label="系统操作"), allow_empty=False
    )
    subject_scopes = serializers.ListField(label="授权对象", child=RoleScopeSubjectSLZ(label="授权对象"), allow_empty=False)


class ManagementGradeManagerUpdateSLZ(serializers.Serializer):
    name = serializers.CharField(label="分级管理员名称", max_length=128, required=False)
    description = serializers.CharField(label="描述", allow_blank=True, required=False)

    authorization_scopes = serializers.ListField(
        label="可授权的权限范围",
        child=ManagementRoleScopeAuthorizationSLZ(label="系统操作"),
        required=False,
        allow_empty=False,
    )
    subject_scopes = serializers.ListField(
        label="授权对象",
        child=RoleScopeSubjectSLZ(label="授权对象"),
        required=False,
        allow_empty=False,
    )


class ManagementGradeManagerBasicInfoSZL(serializers.Serializer):
    id = serializers.IntegerField(label="分级管理员ID")
    name = serializers.CharField(label="分级管理员名称", max_length=128)
    description = serializers.CharField(label="描述", allow_blank=True)


class ManagementGradeManagerMembersSLZ(serializers.Serializer):
    members = serializers.ListField(child=serializers.CharField(label="成员"), max_length=100)

    def validate(self, data):
        """
        校验成员加入的分级管理员数是否超过限制
        """
        role_check_biz = RoleCheckBiz()
        for username in data["members"]:
            # subject加入的分级管理员数量不能超过最大值
            role_check_biz.check_subject_grade_manager_limit(Subject(type=SubjectType.USER.value, id=username))
        return data


class ManagementGradeManagerMembersDeleteSLZ(serializers.Serializer):
    members = serializers.CharField(label="用户名", help_text="用户名，多个以英文逗号分隔")

    def validate(self, data):
        # 验证 member的合法性，并转化为后续view需要数据格式
        members = data.get("members") or ""
        if members:
            try:
                data["members"] = list(filter(None, members.split(",")))
            except Exception:  # pylint: disable=broad-except
                raise serializers.ValidationError({"members": [f"用户名({members})非法"]})

        if len(data["members"]) == 0:
            raise serializers.ValidationError({"members": "should not be empty"})

        return data


class ManagementGroupBasicInfoSLZ(serializers.Serializer):
    name = serializers.CharField(label="用户组名称", min_length=2, max_length=128)
    description = serializers.CharField(label="描述", min_length=10)


class ManagementGroupBasicCreateSLZ(ManagementGroupBasicInfoSLZ):
    readonly = serializers.BooleanField(label="是否只读", default=True, required=False)


class ManagementGradeManagerGroupCreateSLZ(serializers.Serializer):
    groups = serializers.ListField(child=ManagementGroupBasicCreateSLZ(label="用户组"), max_length=10)

    def validate(self, data):
        """
        groups自身数据是否包括用户重名
        """
        groups_data = data["groups"]
        names = set()
        for g in groups_data:
            if g["name"] in names:
                raise serializers.ValidationError({"groups": [_("用户组名称{}不能重复").format(g["name"])]})
            names.add(g["name"])
        return data


class ManagementGroupBasicSLZ(ManagementGroupBasicInfoSLZ):
    id = serializers.IntegerField(label="用户组ID")


class ManagementGroupBaseInfoUpdateSLZ(serializers.Serializer):
    name = serializers.CharField(label="用户组名称", min_length=2, max_length=128, required=False)
    description = serializers.CharField(label="描述", min_length=10, required=False)


class ManagementGroupMemberSLZ(serializers.Serializer):
    type = serializers.ChoiceField(label="成员类型", choices=GroupMemberType.get_choices())
    id = serializers.CharField(label="成员id")
    name = serializers.CharField(label="名称")
    expired_at = serializers.IntegerField(label="过期时间戳(单位秒)")


class ManagementGroupMemberDeleteSLZ(serializers.Serializer):
    type = serializers.ChoiceField(label="成员类型", choices=GroupMemberType.get_choices())
    ids = serializers.CharField(
        label="成员IDs", help_text="成员IDs，多个以英文逗号分隔, 对于type=user，则ID为用户名，对于type=department，则为部门ID"
    )

    def validate(self, data):
        # 验证 ID的合法性，并转化为后续view需要数据格式
        ids = data.get("ids") or ""
        if ids:
            try:
                data["ids"] = list(filter(None, ids.split(",")))
            except Exception:  # pylint: disable=broad-except
                raise serializers.ValidationError({"ids": [f"成员IDS({ids})非法"]})

        if len(data["ids"]) == 0:
            raise serializers.ValidationError({"ids": "should not be empty"})

        return data


class ManagementGradeManagerBasicSLZ(serializers.Serializer):
    id = serializers.IntegerField(label="分级管理员ID")


class ManagementUserQuerySLZ(serializers.Serializer):
    user_id = serializers.CharField(label="用户名", max_length=32)


class ManagementUserGradeManagerQuerySLZ(ManagementUserQuerySLZ, ManagementSourceSystemSLZ):
    pass


class ManagementGroupGrantSLZ(ManagementRoleScopeAuthorizationSLZ):
    pass


class ManagementGroupRevokeSLZ(ManagementRoleScopeAuthorizationSLZ):
    pass


class ManagementGroupPolicyDeleteSLZ(serializers.Serializer):
    system = serializers.CharField(label="授权的系统id", max_length=32)
    actions = serializers.ListField(label="操作", child=ManagementActionSLZ(label="操作"), allow_empty=False)


class ManagementGroupIDsSLZ(serializers.Serializer):
    group_ids = serializers.ListField(label="用户组ID列表", child=serializers.IntegerField(label="用户组ID"))


class ManagementGroupApplicationCreateSLZ(ManagementGroupIDsSLZ, ExpiredAtSLZ, ReasonSLZ):
    applicant = serializers.CharField(label="申请者的用户名", max_length=32)


class ManagementApplicationIDSLZ(serializers.Serializer):
    ids = serializers.ListField(label="申请单据ID列表", child=serializers.CharField(label="申请单据ID"))
