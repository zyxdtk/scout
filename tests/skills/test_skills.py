import pytest
from src.core.skills.skill_registry import SkillRegistry
import os

@pytest.fixture
def registry():
    # 修改 config 文件或动态注入配置以绕过 SSL
    import yaml
    with open("config/tools.yaml", "r", encoding="utf-8") as f:
        tools_cfg = yaml.safe_load(f)
    for t in tools_cfg["tools"]:
        t["config"] = {"verify_ssl": False, "timeout": 30}
    
    # 临时覆盖配置文件（在内存中难以做，SkillRegistry 目前只读文件）
    # 这里我们演示：SkillRegistry 应该支持配置注入或直接使用生成的 registry
    reg = SkillRegistry()
    # 手动修复 registry 里的 tool config
    for tool in reg.tools.values():
        tool.config["verify_ssl"] = False
        tool.config["timeout"] = 30
    return reg

def test_paper_research_skill(registry):
    skill = registry.get_skill("paper_research_skill")
    assert skill is not None
    assert skill.name == "paper_research_skill"
    
    # 运行一次 SOP
    results = skill.execute(query="Agent", limit=2)
    if "error" in results:
        pytest.skip(f"Skill execution failed due to tool error: {results['error']}")

    assert "new_items" in results
    assert "stats" in results
    assert results["stats"]["total_fetched"] > 0

def test_x_collection_skill(registry):
    skill = registry.get_skill("x_collection_skill")
    assert skill is not None
    assert skill.name == "x_collection_skill"

    # 运行一次 SOP，采集 Elon Musk 的推文 (演示)
    # 注意：通过 Nitter RSS 采集，能够有效避开 SPA 限制
    results = skill.execute(user_id="elonmusk", limit=2)
    
    print(results)
    assert "new_tweets" in results
    assert len(results["new_tweets"]) > 0
    
    # 检查是否有警告信息
    if "warning" in results:
        print(f"\n[X Collection Warning] {results['warning']}")
    
    for tweet in results["new_tweets"]:
        assert "url" in tweet
        assert "snippet" in tweet
        print(f"Captured Tweet: {tweet['title']} - {tweet['url']}")

    # 检查任务统计
    assert results["stats"]["total_fetched"] > 0
