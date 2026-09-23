# dows-hrm


## database/mysql:ems/数据库


### module/dows-uim/用户


#### table/userInstance/用户实例


##### bigint/userInstanceId/用户ID


##### bigint/operatorId/操作者ID


##### varchar/userName/用户名


##### varchar/identifyNo/身份证号


##### integer/userAge/用户年龄


##### integer/sex/性别


##### varchar/appId/应用ID


##### integer/ver/乐观锁, 默认: 0


##### datetime/ts/时间戳


#### table/UserAddress/用户地址


##### bigint/UserAddressId/用户-地址维度ID


###### pk/1/


###### required/1/


###### notnull/1/


##### bigint/operatorId/操作者ID


##### bigint/UserInstanceId/用户实例ID


##### varchar/country_no/国家编号


##### varchar/country_name/国家


##### varchar/country_code/国家简称


##### varchar/province_no/省编号


##### varchar/province_name/省名称


##### varchar/province_code/省简称


##### varchar/city_no/城市编号


##### varchar/city_name/城市名


##### varchar/city_code/市简称


##### varchar/address/详细地址


##### varchar/street_no/街道编码


##### varchar/street_name/街道名称


##### varchar/district_no/区县编码


##### varchar/district_name/区县名称


##### varchar/zip_code/邮编


##### varchar/bizline/业务线


##### integer/typ/地址类型


##### integer/state/状态


##### integer/ver/乐观锁, 默认: 0


##### tinyint/deleted/逻辑删除  0未删除  1 删除


##### datetime/ts/时间戳


#### table/UserFamily/用户家庭


##### bigint/UserFamilyId/用户家庭ID


###### pk/1/


###### required/1/


###### notnull/1/


##### bigint/operatorId/操作者ID


##### bigint/UserInstanceId/用户实例ID


##### bigint/memberId/成员ID[用户ID]


##### varchar/relation/关系[父亲|母亲|丈夫|妻子|兄弟|儿子|女儿]


##### datetime/buildTime/组建时间


##### tinyint/householder/是否户主[0:否，1：是]


##### integer/state/状态


##### integer/ver/乐观锁, 默认: 0


##### tinyint/deleted/逻辑删除  0未删除  1 删除


##### datetime/ts/时间戳


#### table/UserJob/用户工作


##### bigint/UserJobId/用户工作信息ID


##### bigint/UserInstance/用户实例ID


##### varchar/profession/职业


##### varchar/orgName/工作单位名称


##### varchar/unit/单位[日|月|年]


##### datetime/startTime/开始时间


##### datetime/endTime/结束时间


##### integer/duration/时长


##### integer/state/状态


##### integer/ver/乐观锁, 默认: 0


##### varchar/appId/应用ID


##### tinyint/deleted/逻辑删除  0未删除  1 删除


##### bigint/operatorId/操作者ID


##### datetime/ts/时间戳


#### table/UserEducation/用户教育


##### bigint/UserEducationId/用户教育ID


##### bigint/operatorId/操作者ID


##### bigint/UserInstance/用户实例ID


##### varchar/application/专业名称


##### varchar/universityName/学校名称


##### varchar/applicationDescription/专业描述


##### datetime/startTime/开始年月


##### datetime/endTime/结束年月


##### integer/educationType/性质：0-职业学院，1-专科，2-本科，3-硕士，4-博士


##### tinyint/currentToday/至今


##### tinyint/deleted/逻辑删除  0未删除  1 删除


##### varchar/appId/应用ID


##### datetime/ts/时间戳


#### table/UserTraining/用户培训


##### bigint/UserTrainingId/用户培训ID


##### bigint/operatorId/操作者ID


##### bigint/UserInstance/用户实例ID


##### varchar/universityName/机构名称


##### varchar/trainingDescription/培训描述


##### varchar/appId/应用ID


##### datetime/startTime/开始年月


##### datetime/endTime/结束年月


##### datetime/ts/时间戳


##### tinyint/deleted/逻辑删除  0未删除  1 删除


#### table/UserCertication/用户证书


##### bigint/UserCerticationId/用户证书ID


##### bigint/operatorId/操作者ID


##### bigint/UserInstance/用户实例ID


##### varchar/certName/证书名称


##### varchar/certNo/证书编号


##### varchar/appId/应用ID


##### tinyint/perminent/永久性标识：0-否，1-是


##### datetime/awardDate/证书获取日期


##### datetime/expiryDate/证书有效日期


##### tinyint/deleted/逻辑删除  0未删除  1 删除


##### datetime/ts/时间戳


#### table/UserContact/用户联系人


##### bigint/UserContactId/用户联系人ID


###### pk/1/


###### required/1/


###### notnull/1/


##### bigint/UserInstance/用户实例ID


##### varchar/contact/联系人


##### varchar/contactNum/联系号码


##### integer/contactTyp/联系类型（0:手机，1:邮箱，2:电话）


##### integer/sorted/排序


##### integer/self/是否是自己


##### integer/state/状态


##### integer/ver/乐观锁, 默认: 0


##### bigint/operatorId/操作者ID


##### tinyint/deleted/逻辑删除  0未删除  1 删除


##### datetime/ts/时间戳


#### table/orgTree/组织树


##### bigint/orgTreeId/组织树ID


###### pk/1/


###### required/1/


###### notnull/1/


##### bigint/pid/父ID


##### bigint/operatorId/操作者ID


##### varchar/orgName/组织名


##### varchar/orgCode/组织码


##### varchar/orgAvator/组织头像


##### varchar/idPath/ID路径


##### varchar/namePath/名称路径


##### varchar/appId/应用ID


##### integer/ver/版本


##### tinyint/deleted/逻辑删除  0未删除  1 删除


##### datetime/ts/时间戳


#### table/orgNode/组织节点


##### bigint/orgNodeId/组织节点ID


###### pk/1/


###### required/1/


###### notnull/1/


##### bigint/orgTreeId/组织树ID


##### bigint/accountInstanceId/账号实例ID


##### bigint/userInstanceId/用户ID


##### varchar/aliasName/组别名


##### varchar/appId/应用ID


##### integer/ver/版本


##### bigint/operatorId/操作者ID


##### tinyint/deleted/逻辑删除  0未删除  1 删除


##### datetime/ts/时间戳


#### table/orgRole/组织角色


##### bigint/orgRoleId/组织角色ID


###### pk/1/


###### required/1/


###### notnull/1/


##### bigint/orgTreeId/组织树ID


##### bigint/rbacRoleId/角色实例ID


##### bigint/operatorId/操作者ID


##### integer/ver/乐观锁, 默认: 0


##### varchar/appId/应用ID


##### tinyint/deleted/逻辑删除  0未删除  1 删除


##### date/ts/时间戳


#### table/orgInfo/组织信息


##### bigint/orgInfoId/组织信息ID


###### pk/1/


###### required/1/


###### notnull/1/


##### bigint/orgRoleId/组织角色ID


##### bigint/orgTreeId/组织树ID


##### bigint/operatorId/操作者ID


##### integer/ver/乐观锁, 默认: 0


##### varchar/appId/应用ID


##### tinyint/deleted/逻辑删除  0未删除  1 删除


##### date/ts/时间戳


#### table/orgRule/岗位规则


##### bigint/orgRuleId/岗位规则ID


###### pk/1/


##### bigint/orgTreeId/组织树ID


##### varchar/ruleName/规则名称


##### varchar/ruleDescription/规则描述


##### bigint/operatorId/操作者ID


##### tinyint/enabled/是否可用0-可用，1-不可用


##### varchar/appId/应用ID


##### datetime/ts/时间戳


#### table/orgAction/岗位行动


##### bigint/orgActionId/岗位行动ID


###### pk/1/


##### bigint/orgRuleId/岗位规则ID


##### bigint/operatorId/操作者ID


##### integer/seq/动作顺序


##### varchar/actionName/动作名称


##### varchar/actionDescription/岗位动作描述


##### varchar/appId/应用ID


##### datetime/ts/时间戳


#### table/orgIndicator/岗位指标


##### bigint/orgIndicatorId/岗位指标ID


###### pk/1/


##### bigint/orgActionId/岗位行动ID


##### varchar/indicatorName/指标名称


##### varchar/indicatorKeyword/指标关键字


##### integer/indicatorScore/指标分值


##### integer/matchScore/指标匹配度


##### tinyint/enabled/是否可用0-可用，1-不可用


##### bigint/operatorId/操作者ID


##### varchar/appId/应用ID


##### datetime/ts/时间戳


#### table/orgKnowledge/岗位知识


##### bigint/orgKnowledge/岗位知识ID


###### pk/1/


##### bigint/orgTreeId/组织树ID


##### bigint/orgRuleId/岗位规则ID


##### bigint/operatorId/操作者ID


##### bigint/referenceId/引用的知识ID，可以来自[hrm,exam...]


##### varchar/referenceTable/来源表，可以来自[hrm,exam]表


##### varchar/contentUri/内容资源


##### varchar/appId/应用ID


##### datetime/ts/时间戳


#### table/orgJd/岗位JD


##### bigint/orgJdId/岗位描述ID


###### pk/1/


##### bigint/orgTreeId/组织树ID


##### varchar/description/岗位描述


##### varchar/channels/发布渠道集合


##### varchar/appId/应用ID


##### datetime/ts/时间戳


#### table/accountUser/账号用户


##### bigint/accountUserId/账号用户ID


###### pk/1/


###### required/1/


###### notnull/1/


##### bigint/accountInstanceId/账号实例ID


##### bigint/userInstanceId/用户ID


##### bigint/operatorId/操作者ID


##### varchar/appId/应用ID


##### integer/ver/乐观锁, 默认: 0


##### tinyint/deleted/逻辑删除  0未删除  1 删除


##### datetime/ts/时间戳


#### table/accountInstance/账号实例


##### bigint/accountInstanceId/账号实例ID


###### pk/1/


###### required/1/


###### notnull/1/


##### varchar/identifier/账号标识符


##### varchar/password/密码


##### varchar/zoneNo/区域编码(+86，+11...)


##### varchar/cellphone/手机号


##### varchar/avator/头像


##### varchar/referralsNo/推荐码


##### varchar/source/来源(来源渠道推广时标记用)


##### varchar/appId/应用ID


##### bigint/operatorId/操作者ID


##### integer/ver/乐观锁, 默认: 0


##### tinyint/deleted/逻辑删除  0未删除  1 删除


##### datetime/ts/时间戳


#### table/accountIdentifier/账号标识


##### bigint/accountIdentifierId/账号标识ID


###### pk/1/


###### required/1/


###### notnull/1/


##### varchar/identifier/账号标识符


##### bigint/operatorId/操作者ID


##### integer/type/类型[0:账号,1:手机号,2:邮箱,3:第三方token]


##### integer/ver/乐观锁, 默认: 0


##### varchar/appId/应用ID


##### tinyint/deleted/逻辑删除  0未删除  1 删除


##### datetime/ts/时间戳


#### table/accountRelation/账号推荐人


##### bigint/accountRelationId/账号关系ID


###### pk/1/


###### required/1/


###### notnull/1/


##### bigint/accountReferrerId/账号推荐人ID


##### bigint/accountInstanceId/账号实例ID


##### bigint/operatorId/操作者ID


##### bigint/operatorId/操作者ID


##### integer/ver/乐观锁, 默认: 0


##### varchar/appId/应用ID


##### tinyint/deleted/逻辑删除  0未删除  1 删除


##### datetime/ts/时间戳


#### table/accountType/账号类型


##### bigint/accountTypeId/账号类型ID


###### pk/1/


###### required/1/


###### notnull/1/


##### bigint/operatorId/操作者ID


##### bigint/accountInstanceId/账号实例ID


##### bigint/userInstanceId/用户ID


##### bigint/referenceId/引用ID(商户表中的ID)


##### varchar/typeName/类型名称[代理商,商户]来自字典表


##### integer/typeValue/类型值(来自字典表)


##### integer/ver/乐观锁, 默认: 0


##### varchar/appId/应用ID


##### tinyint/deleted/逻辑删除  0未删除  1 删除


##### datetime/ts/时间戳


#### table/accountRole/账号角色


##### bigint/accountRoleId/账号角色ID


###### pk/1/


###### required/1/


###### notnull/1/


##### bigint/accountInstanceId/账号实例ID


##### bigint/rbacRoleId/角色实例ID


##### bigint/operatorId/操作者ID


##### integer/ver/乐观锁, 默认: 0


##### varchar/appId/应用ID


##### tinyint/deleted/逻辑删除  0未删除  1 删除


##### datetime/ts/时间戳


### module/dows-hrm/人力资源


#### table/examItem/试题题项


##### bigint/examItemId/试题题项ID


###### pk/1/


##### varchar/knowledgeCatelog/知识类目


##### varchar/knowledgeName/题目名称


##### varchar/itemDescription/题目描述


##### varchar/optionJson/题目答案选项描述


##### varchar/itemAnswer/结果选项


##### smallint/itemScore/题目分值


##### integer/itemType/题型[1:选择题，2:填空题，3：..]


##### tinyint/enabled/是否可用0-可用，1-不可用


##### bigint/operatorId/操作者ID


##### varchar/appId/应用ID


##### datetime/ts/时间戳


#### table/examConfig/考试配置


##### bigint/examConfigId/考试配置ID


##### bigint/orgTreeId/组织树ID


##### bigint/operatorId/操作者ID


##### varchar/knowledgeCatelog/知识类目


##### varchar/dataTable/数据来源表


##### text/examItemIds/试题ID集合(用，分割)


##### varchar/template/试卷模板


##### integer/strategy/策略[0:顺序，1:随机]


##### integer/paperCount/试卷数量


##### integer/duration/考试时长


##### tinyint/merged/是否合并分类


##### tinyint/random/是否随机出题


##### varchar/appId/应用ID


##### datetime/ts/时间戳


#### varchar/examPaper/考试试卷


##### bigint/examPaperId/考试试卷ID


##### bigint/examConfigId/考试配置ID


##### varchar/content/试卷内容（freemarker渲染生成）


##### varchar/link/试卷链接


##### varchar/appId/应用ID


##### datetime/ts/时间戳


#### table/examInstance/考试实例


##### bigint/examInstanceId/考试实例ID


###### pk/1/


##### bigint/examPaperId/考试试卷ID


##### bigint/resumeInstanceId/人才简历ID


##### bigint/accountInstanceId/账号实例ID


##### bigint/userInstanceId/用户实例ID


##### varchar/examInstanceName/实例名称[人名+题目类型]


##### datetime/startTime/开始考试时间


##### datetime/endTime/结束考试时间


##### datetime/finishTime/完成时间


##### integer/examDuration/考试时长


##### tinyint/enabled/是否可用0-可用，1-不可用


##### bigint/operatorId/操作者ID


##### varchar/appId/应用ID


##### datetime/ts/时间戳


#### table/examAnswer/考试答题


##### bigint/examQuestionId/考试试题ID


###### pk/1/


##### bigint/examInstanceId/考试实例ID


##### bigint/examItemId/题项ID


##### integer/itemScore/问题分值


##### integer/examScore/考得分值


##### bigint/operatorId/操作者ID


##### varchar/appId/应用ID


##### datetime/ts/时间戳


#### table/resumeInstance/人才简历


##### bigint/resumeInstanceId/人才简历ID


###### pk/1/


##### bigint/accountInstanceId/账号实例ID


###### pk/1/


###### required/1/


###### notnull/1/


##### bigint/UserInstanceId/用户实例ID


##### varchar/resumeLink/简历链接


##### varchar/resumeDoc/简历文件


##### varchar/md5/简历md5


##### varchar/source/简历来源[boss|lagou|...]


##### varchar/applierName/申请人名称


##### varchar/applierEmail/申请人邮箱


##### varchar/applierMobile/申请人手机号


##### varchar/appliedPosition/申请岗位


##### integer/version/版本


##### boolean/selected/是否通过AI简历筛选


##### boolean/confirmed/人力是否面试确认


##### bigint/operatorId/操作者ID


##### varchar/appId/应用ID


##### datetime/interviewDate/预约面试日期


##### datetime/ts/时间戳


#### table/resumeProject/简历项目


##### bigint/resumeProjectId/简历项目ID


##### bigint/resumeInstanceId/人才简历ID


##### barchar/companyName/公司名称


##### varchar/positionName/岗位名称


##### varchar/projectName/项目名称


##### varchar/projectDescription/项目描述


##### varchar/projectTechnology/项目技术描述


##### datetime/projectStartTime/开始时间


##### datetime/projectFinishTime/结束时间


##### tinyint/enabled/是否可用0-可用，1-不可用


##### bigint/operatorId/操作者ID


##### varchar/appId/应用ID


##### datetime/ts/时间戳


#### table/interviewInstance/面试实例


##### bigint/interviewInstanceId/面试实例ID


###### pk/1/


##### bigint/resumeInstanceId/人才简历ID


##### bigint/interviewerId/面试官ID(账号ID)


##### bigint/intervieweeId/面试者ID(账号ID)


##### bigint/operatorId/操作者ID(账号ID)


##### integer/interviewDuration/面试时长


##### integer/interviewType/面试形式[线下|线上]


##### integer/matchScore/匹配度


##### integer/interviewScore/面试分值


##### integer/seq/序号[1面，2面]


##### datetime/startTime/开始面试时间


##### datetime/endTime/结束面试时间


##### varchar/interviewEvaluate/面试评价


##### varchar/interviewContent/面试内容记录


##### varchar/contentLink/内容链接[腾讯会议记录链接,飞书会议记录链接]


##### varchar/appId/应用ID


##### datetime/ts/时间戳


#### table/interviewResult/面试结果


##### bigint/interviewResultId/面试结果ID


##### bigint/resumeInstanceId/人才简历ID


##### bigint/accountInstanceId/面试者账号ID


##### bigint/userInstanceId/面试者用户ID


##### varchar/userName/面试者名称


##### decimal/examScore/考试分值(通过resumeInstanceId查询examInstance表并计算)


##### decimal/interviewScore/面试分值(通过resumeInstanceId查询interviewInstance表并计算)


##### decimal/score/面试总分(由examScore+interviewScore)


##### boolean/passed/是否通过


##### bigint/operatorId/操作者ID


##### varchar/appId/应用ID


##### datetime/ts/时间戳


#### table/interviewStatistics/面试统计


##### bigint/interviewStatisticsId/面试统计ID


###### pk/1/


##### bigint/resumeInstanceId/人才简历ID


##### bigint/userInstanceId/用户ID


##### varchar/appliedPosition/申请岗位


##### varchar/jobType/工作方式[1-兼职，2-合作，3-全职]


##### varchar/reason/未入职原因


##### datetime/entryTime/入职时间


##### integer/appliedCount/申请次数


##### integer/interviewCount/面试次数


##### tinyint/entryed/是否已入职[0-入职，1-未入职]


##### bigint/operatorId/操作者ID


##### varchar/appId/应用ID


##### datetime/ts/操作时间


### module/dows-rbac/权限


#### table/rbac_role/角色实例


##### bigint/rbacRoleId/角色id


###### pk/1/


###### required/1/


###### notnull/1/


##### bigint/pid/角色父ID(角色组|继承)


##### varchar/roleName/角色名称


##### varchar/roleCode/角色编码


##### varchar/roleIcon/角色图标


##### varchar/idPath/id路径


##### varchar/namePath/名称路径


##### varchar/codePath/菜单路径URI[menuPath]


##### varchar/appId/应用id


##### varchar/description/描述


##### integer/roleLevel/角色级别


##### tinyint/inherit/当前角色是否继承父角色对应的权限


##### tinyint/state/状态


##### tinyint/deleted/逻辑删除  0未删除  1 删除


##### datetime/ts/时间戳


#### table/rbac_permission/角色权限集


##### bigint/rbacPermissionId/权限ID


###### pk/1/


###### required/1/


###### notnull/1/


##### bigint/rbacRoleId/角色id


##### bigint/rolePid/父角色ID(继承时该字段有值)


##### bigint/resourceId/资源ID


##### varchar/appId/应用id 从角色冗余


##### varchar/description/描述


##### varchar/resourceTable/资源表


##### integer/resourceType/资源类型[0:接口，1:菜单]


##### integer/state/状态


##### integer/ver/乐观锁, 默认: 0


##### tinyint/deleted/逻辑删除  0未删除  1 删除


##### datetime/ts/时间戳


#### table/rbac_group/资源组


##### bigint/rbacGroupId/角色权限组ID


###### pk/1/


###### required/1/


###### notnull/1/


##### varchar/groupName/组名称


##### varchar/groupCode/组CODE


##### varchar/description/描述


##### varchar/appId/应用id 


##### varchar/resourceIds/资源ID集合逗号分割


##### varchar/resourceTable/资源表


##### integer/resourceType/资源类型[0:接口，1:菜单]


##### integer/state/状态


##### integer/ver/乐观锁, 默认: 0


##### tinyint/deleted/逻辑删除  0未删除  1 删除


##### datetime/ts/时间戳


#### table/rbac_uri/接口集


##### bigint/rbacUriId/接口ID


###### pk/1/


###### required/1/


###### notnull/1/


##### bigint/rbacMenuId/菜单ID


##### varchar/uriName/接口名称


##### varchar/uriCode/接口CODE


##### varchar/label/页面功能标签[按钮、链接]


##### varchar/uri/接口链接


##### varchar/configJson/JSON数据集


##### varchar/appId/应用id


##### integer/customed/自定义


##### varchar/description/描述


##### integer/ver/乐观锁, 默认: 0


##### tinyint/shared/是否共享[0:不共享,1:共享]


##### tinyint/state/状态


##### tinyint/deleted/逻辑删除  0未删除  1 删除


##### datetime/ts/时间戳


#### table/rbac_menu/菜单集


##### bigint/rbacMenuId/菜单ID


###### pk/1/


###### required/1/


###### notnull/1/


##### bigint/rbacRoleId/角色id


##### bigint/pid/菜单父ID


##### varchar/menuName/菜单名称


##### varchar/menuCode/菜单CODE


##### varchar/idPath/ID路径


##### varchar/namePath/名称路径


##### varchar/codePath/菜单路径URI[menuPath]


##### varchar/configJson/配置JSON{vue:compent-path}


##### varchar/menuIcon/图标


##### varchar/menuPath/前端路由路径


##### varchar/redirect/跳转路径


##### varchar/appId/应用id


##### integer/seq/排序


##### integer/openType/打开类型[0:page,1:api,2:......]


##### integer/ver/乐观锁, 默认: 0


##### tinyint/visible/是否隐藏


##### tinyint/isframe/是否框架


##### tinyint/state/状态


##### tinyint/deleted/逻辑删除  0未删除  1 删除


##### datetime/ts/时间戳


#### table/RbacRule/数据规则


##### bigint/RbacRuleId/数据规则ID


###### pk/1/


##### bigint/rbacRoleId/角色ID


##### varchar/role_code/角色CODE


##### varchar/ruleDescription/规则描述


##### varchar/dataTable/数据表名称


##### varchar/app_id/应用 id


##### varchar/expression/基于元数据构成的规则表达式json


###### length/2048/


###### select * from rbac_role where org_id=''  and  crucives()


##### varchar/selects/筛选字段','分割


##### integer/dataScop/数据范围[0:所有数据,1:所在组及子组数据,2:所在组数据,3:本人数据]


##### integer/sorted/排序


##### varchar/lastExpression/末尾Expression


##### integer/ver/乐观锁, 默认: 0


##### tinyint/deleted/是否逻辑删除: 0 未删除(false), 1 已删除(true); 默认: 0


##### datetime/ts/时间戳


### module/dows-pay/支付


#### table/PayChannel/支付通道


##### bigint/PayChannelId/支付通道ID


##### varchar/channelNo/通道编号(全局唯一)


##### varchar/channelName/通道名称


##### varchar/channelCode/通道码


##### varchar/channelHome/支付页面


##### varchar/description/描述


##### boolean/deleted/逻辑删除


##### datetime/ts/时间戳


#### table/PayAccount/支付通道账号


##### bigint/PayAccountId/支付通道账号ID


##### bigint/pid/父ID


##### varchar/channelNo/通道编号(全局唯一)


##### varchar/channelCode/通道码


##### varchar/channelAccount/通道账号


##### varchar/channelMerchantNo/通道商户号


##### varchar/merchantNo/商户号


##### varchar/accountNo/账号


##### integer/cat/通道账号类型（0：个人账号，1：商户账号，11：商户子账号....）


##### integer/state/状态


##### datetime/ts/时间戳


##### boolean/deleted/逻辑删除


#### table/PayApi/支付通道接口


##### bigint/PayApiId/支付通道接口ID


##### varchar/apiNo/接口编号


##### varchar/channelNo/通道编号(全局唯一)


##### varchar/channelCode/通道码


##### varchar/apiName/接口名称


##### varchar/apiCode/接口namespace


##### varchar/apiParams/接口参数


##### varchar/apiUri/接口URI


##### varchar/redirectUrl/接口重定向URL


##### varchar/notifyUrl/接口通知地址


##### varchar/env/环境（dev|test|ped|....)


##### varchar/description/描述


##### datetime/ts/时间戳


##### boolean/deleted/逻辑删除


#### table/PayCode/支付通道状态码


##### bigint/PayCodeId/支付通道状态码ID


##### varchar/codeNo/统一状态码编号


##### varchar/apiNo/接口编号


##### varchar/channelNo/通道编号(全局唯一)


##### varchar/channel_name/通道名称


##### varchar/channel_code/通道码


##### varchar/channel_state_code/通道状态码


##### varchar/channel_state_descr/通过状态码描述


##### varchar/status_code/统一状态码


##### varchar/status_descr/统一状态码描述


##### varchar/methodNo/方法编号（一个方法可能存在多个code）


##### datetime/ts/时间戳


##### boolean/deleted/逻辑删除


#### table/PayBiz/支付业务


##### bigint/PayBizId/支付业务ID


##### bigint/pid/父ID


##### varchar/bizNo/业务编号


##### varchar/bizCode/业务code


##### varchar/bizName/业务名称|业务组名称


##### varchar/bizNamespace/名称空间


##### varchar/ruleNo/规则编号或ID


##### varchar/ruleName/规则名称


##### int/state/状态


##### decimal/price/价格


##### datetime/ts/时间戳


##### boolean/deleted/逻辑删除


#### table/PayMethod/支付方法


##### bigint/PayMethodId/支付方法ID


##### varchar/methodNo/方法编号


##### varchar/methodName/方法名称


##### varchar/methodNamespace/方法名称空间


##### varchar/methodParams/方法参数


##### varchar/methodUri/方法URI


##### varchar/redirectUrl/重定向URL


##### varchar/notifyUrl/通知URL


##### varchar/payTyp/支付业务类型(......)


##### varchar/env/环境（dev|test|ped|....)


##### varchar/bizGroup/业务组名称


##### varchar/descr/描述


##### datetime/dt/时间戳


##### boolean/deleted/逻辑删除


#### table/PayDirective/支付指令集


##### bigint/PayDirectiveId/支付指令集ID


##### varchar/directiveNo/指令编号


##### varchar/methodNo/方法编号


##### varchar/apiNo/接口编号


##### varchar/methodNamespace/方法名称空间（bizNamespace）


##### varchar/payTyp/支付业务类型(......)


##### varchar/env/环境（dev|test|ped|....)


##### varchar/bizNo/业务编号


##### varchar/bizName/业务名称


##### int/state/状态


##### datetime/ts/时间戳


##### boolean/deleted/逻辑删除


#### table/PayRule/支付规则


##### bigint/PayRuleId/支付规则ID


##### varchar/ruleNo/规则编号


##### varchar/ruleName/规则名称


##### varchar/ruleCode/规则码


##### varchar/ruleExpr/提取表达式(sql://*；el://)


##### varchar/dataApi/提取接口，业务方提供，参数为ruleExpr，根据cron表达式


##### varchar/channelNo/通道编号(全局唯一)


##### varchar/merchantNo/商户号


##### boolean/deleted/逻辑删除


##### datetime/ts/时间戳


#### table/PayInstance/支付通道实例


##### bigint/PayInstanceId/支付通道实例ID


##### varchar/instanceNo/支付通道实例编号


##### varchar/channelNo/通道编号(全局唯一)


##### varchar/channelCode/通道码（alipay|weixin|......）


##### varchar/channelAppId/通道应用ID


##### varchar/serviceUrl/网关URL


##### varchar/msgUrl/消息推送URL


##### varchar/charset/字符集


##### varchar/format/格式


##### varchar/signType/签名类型(RSA/RSA2/....)


##### varchar/certModel/验证模式(公钥模式：psk:0,证书模式：crt:1)


##### varchar/privateKey/私钥


##### varchar/payPublicKey/公钥


##### varchar/appCertPath/应用公钥证书路径


##### varchar/payCertPath/公钥证书文件路径


##### varchar/payRootCertPath/CA根证书文件路径


##### varchar/secret_key/加密签名密钥


##### varchar/env/环境（dev|test|ped|....)


##### varchar/merchantNo/平台商户号


##### varchar/accountNo/账号


##### varchar/appId/应用ID


##### varchar/tenantId/租户号


##### int/state/状态


##### datetime/ts/时间戳


##### boolean/deleted/逻辑删除


#### table/PayService/支付接入服务


##### bigint/PayService/支付接入服务


##### varchar/applyNo/申请编号


##### varchar/merchantNo/商户号


##### varchar/appId/全局唯一应用ID


##### varchar/appUrl/应用链接


##### decimal/price/价格


##### varchar/callbackApi/对业务方的回调接口


##### varchar/directiveNo/指令编号或ID


##### int/directiveTyp/指令类型


##### varchar/ruleNo/规则编号或ID


##### varchar/ruleName/规则名称


##### boolean/checked/审核是否通过（0:否，1：是）


##### boolean/deleted/逻辑删除


##### datetime/ts/时间戳


#### table/PayApply/支付申请


##### bigint/PayApplyId/支付申请ID


##### varchar/applyNo/申请编号


##### varchar/merchantNo/商户号


##### varchar/appId/全局唯一应用ID


##### varchar/appUrl/应用链接


##### decimal/price/价格


##### varchar/bizNo/业务编号


##### varchar/bizName/业务名称|业务组名称


##### boolean/checked/审核是否通过（0:否，1：是）


##### boolean/deleted/逻辑删除


##### datetime/dt/时间戳


#### table/PayMerchant/支付商户


##### bigint/PayMerchantId/支付商户ID


##### varchar/merchantNo/平台商户号


##### varchar/payAccount/内部支付账号


##### varchar/payPwd/内部支付密码


##### varchar/accountName/内部账号名


##### varchar/accountNo/内部账号


##### varchar/app_id/应用id


##### varchar/tentantNo/租户号


##### int/state/状态


##### boolean/deleted/逻辑删除


##### datetime/ts/时间戳


#### table/PayTransaction/支付交易


##### bigint/PayTransactionId/支付交易ID


##### varchar/transactionNo/交易号


##### varchar/transactionName/交易名称


##### varchar/payChannel/支付通道


##### varchar/orderId/订单号


##### varchar/orderTitle/订单标题


##### varchar/merchantNo/商户号


##### varchar/merchantName/商户名称


##### varchar/dealForm/交易form方(accountNO)


##### varchar/dealTo/交易to方(accountNo)


##### decimal/amount/交易金额


##### varchar/remark/备注


##### varchar/appId/应用id


##### integer/state/交易状态


##### datetime/transactionTime/交易时间


##### datetime/ts/时间戳


##### boolean/deleted/逻辑删除


#### table/payAllocation/支付分账


##### bigint/payAllocationId/支付分账ID


##### decimal/alloted_amount/实际分得金额（订单实际分账金额, 单位：分（订单金额 - 商户手续费 - 已退款金额））


##### decimal/allot_amount/应分金额（计算该接收方的分账金额,单位分）


##### decimal/pay_order_amount/订单金额,单位分


##### varchar/pay_order_id/系统支付订单号


##### varchar/allot_id/分账记录ID


##### varchar/merchant_name/商户名称


##### varchar/merchant_no/商户号


##### varchar/app_id/应用ID


##### varchar/account_id/分账接收者ID(统一账号ID)快照


##### varchar/account_name/接收者账号别名快照


##### varchar/user_name/接收者姓名快照


##### varchar/batch_order_id/系统分账批次号


##### varchar/channel_code/服务商编码


##### varchar/channel_app_id/通道应用ID


##### varchar/channel_order_no/支付订单渠道支付订单号


##### varchar/channel_account_no/分账接收账号快照


##### varchar/channel_account_name/分账接收账号名称快照


##### varchar/channel_batch_order_id/上游分账批次号


##### tinyint/merchant_type/类型: 1-普通商户, 2-特约商户(服务商模式)


##### tinyint/channel_account_type/分账接收账号类型: 0-个人(对私) 1-商户(对公)快照


##### tinyint/state/状态: 0-待分账 1-分账成功, 2-分账失败


##### decimal/allocation_profit/分账比例快照> 配置的实际分账比例


##### tinyint/deleted/逻辑删除


#### table/payLedger/支付账本


##### bigint/payLedgerId/支付账本ID


##### varchar/instance_no/支付通道实例编号


##### varchar/merchant_no/商户号


##### varchar/app_id/应用ID


##### varchar/request_no/请求编号


##### varchar/account_id/分账接收者ID(统一账号ID)


##### varchar/account_name/接收者账号别名


##### varchar/user_name/用户真实名


##### varchar/channel_id/通道ID


##### varchar/channel_code/服务商code


##### varchar/channel_app_id/通道应用ID


##### varchar/channel_account_no/分账接收账号（支付宝|微信等第三方通道账号[账号ID,支付宝账接收方方类型，userId：表示是支付宝账号对应的支付宝唯一用户号；]）


##### varchar/channel_account_name/分账接收账号名称（第三方通道账号，如支付宝loginName：表示是支付宝登录号名|微信）


##### tinyint/channel_account_type/分账接收账号类型: 0-个人(对私) 1-商户(对公)


##### tinyint/state/分账状态（本系统状态，并不调用上游关联关系）: 1-正常分账, 0-暂停分账


##### decimal/allocation_profit/分账比例


##### tinyint/deleted/逻辑删除


##### datetime/ts/时间戳


#### table/payRecord/分账记录


##### bigint/payRecordId/分账记录ID


##### varchar/order_id/订单ID


##### varchar/merchant_no/商户号


##### varchar/app_id/应用ID


##### varchar/account_id/分账接收者ID(统一账号ID)


##### varchar/account_name/接收者账号别名


##### varchar/user_name/用户真实名


##### varchar/channel_code/服务商code


##### varchar/channel_app_id/通道应用ID


##### varchar/channel_account_no/分账接收账号（支付宝|微信等第三方通道账号[账号ID,支付宝账接收方方类型，userId：表示是支付宝账号对应的支付宝唯一用户号；]）


##### varchar/channel_account_name/分账接收账号名称（第三方通道账号，如支付宝loginName：表示是支付宝登录号名|微信）


##### tinyint/channel_account_type/分账接收账号类型: 0-个人(对私) 1-商户(对公)


##### decimal/allocation_profit/分账比例


##### decimal/amount/分账金额


##### varchar/result/请求结果


##### integer/state/请求状态


##### tinyint/deleted/逻辑删除


##### datetime/ts/时间戳


## function/java/接口


### module/github:org.dows.cloud:dows-uim:1.0.0-SNAPSHOT/用户身份


#### rest/org/岗位


##### group/admin/管理端


###### post/config.role/配置角色


- in/array/入参

  - bigint/orgTreeId/组织树ID

  - bigint/rbacRoleId/角色实例ID

- out/boolean/响应

###### post/config.jobRule/配置规则


- in/object/入参

  - bigint/orgRuleId/岗位规则ID

  - bigint/orgTreeId/组织树ID

  - varchar/ruleName/规则名称

  - varchar/ruleDescription/规则描述

  - array/object:lorgAction/岗位动作

    - bigint/orgActionId/岗位行动ID

    - bigint/orgRuleId/岗位规则ID

    - bigint/operatorId/操作者ID

    - integer/seq/动作顺序

    - varchar/actionName/动作名称

    - varchar/actionDescription/岗位动作描述

    - object/list:orgIndicator/岗位指标

      - bigint/orgIndicatorId/岗位指标ID

      - bigint/orgActionId/岗位行动ID

      - varchar/indicatorName/指标名称

      - varchar/indicatorKeyword/指标关键字

      - integer/indicatorScore/指标分值

      - integer/matchScore/指标匹配度

- out/varchar/响应

  - bigint/orgRuleId/岗位规则ID

- requirment//

  - 校验同一岗位规则不能有相同的岗位动作orgActionId

  - 校验同一Action不能有相同的岗位指标orgIndicatorId

##### group/client/客户端


###### get/search.job/搜索岗位


- in/array/入参

  - varchar/jdKeyword/岗位关键字

  - datetime/tsStart/时间戳开始

  - datetime/tsEnd/时间戳结束

- out/array/响应岗位列表

  - bigint/orgJdId/岗位描述ID

  - varchar/description/岗位描述

  - datetime/ts/时间戳

- requirment//

  - 根据关键字搜索岗位信息

  - 根据发布时间段搜索岗位信息

  - 返回岗位列表数据

###### post/post.resume/投递简历


- requirment//

  - 投递简历（简历链接或简历文件）

- in/object/入参

  - bigint/orgJdId/岗位描述ID

  - varchar/resumeLink/简历链接

  - varchar/resumeDoc/简历文件

- out/bigint/响应

### module/github:org.dows.cloud:dows-hrm:1.0.0-SNAPSHOT/人力资源


#### rest/exam/测试


##### group/admin/管理端


###### post/config.paper/配置试卷


- in/object:list/入参

  - bigint/examConfigId/考试配置ID

  - bigint/examItemId/试题题项ID

- out/object/响应

  - bigint/examPaperId/试卷ID

  - varchar/link/试卷链接

###### auto/parse.resume/解析简历


- in/object/入参

  - bigint/resumeInstanceId/人才简历ID

  - object/resumeInstance/简历信息

- out/bigint/响应

###### auto/import.resume/简历生成实例


- in/object/入参

  - bigint/resumeInstanceId/人才简历ID

- out/bigint/响应

  - bigint/accountInstanceId/账号实例ID

###### auto/analyze.resume/AI模型分析简历信息


- in/object/入参

  - bigint/resumeInstanceId/人才简历ID

  - object/resumeInstance/简历信息

- out/bigint/响应

  - bigint/result/成功、失败

###### auto/analyze.interview/面试结果分析


- in/object/入参

  - bigint/resumeInstanceId/人才简历ID

  - bigint/interviewResultId/面试结果ID

- out/bigint/响应

  - bigint/interviewStatisticsId/面试统计ID

###### get/query.interview/查看面试结果分析


- in/object/入参

  - bigint/resumeInstanceId/人才简历ID

- out/bigint/响应

  - bigint/interviewStatisticsId/面试统计ID

  - bigint/interviewResultId/面试结果ID

- requirment//

  - 在面试人员提交完该轮的面试结果后，如果是最后一轮面试，就可以查看面试结果

##### group/client/客户端


###### post/submit.paper/在线考试提交


- in/object/入参

  - bigint/examQuestionId/考试试题ID

    - pk/1/

  - bigint/examInstanceId/考试实例ID

  - bigint/examItemId/题项ID

  - varchar/itemAnswer/结果选项

- out/bigint/响应

  - integer/examScore/考得分值

- requirment//

  - 提交在线考试

  - 能够看到考试结果分数

# 通道接口状态码


# 内部


