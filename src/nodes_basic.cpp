#include <behaviortree_cpp/bt_factory.h>
#include <behaviortree_cpp/action_node.h>
#include <behaviortree_cpp/condition_node.h>
#include <iostream>

using namespace BT;

class BatteryOK : public SyncActionNode
{
public:
    BatteryOK(const std::string &name, const NodeConfig &config)
        : SyncActionNode(name, config) {}
    static PortsList providedPorts()
    {
        return {InputPort<std::string>("vehicle_id"),
                InputPort<double>("min_battery_pct")};
    }
    NodeStatus tick() override
    {
        return NodeStatus::SUCCESS;
    }
};

class WithinGeofence : public SyncActionNode
{
public:
    WithinGeofence(const std::string &name, const NodeConfig &config)
        : SyncActionNode(name, config) {}
    static PortsList providedPorts()
    {
        return {InputPort<std::string>("vehicle_id"),
                InputPort<std::string>("geofence_id")};
    }
    NodeStatus tick() override { return NodeStatus::SUCCESS; }
};

class OutsideRestrictedZone : public SyncActionNode
{
public:
    OutsideRestrictedZone(const std::string &name, const NodeConfig &config)
        : SyncActionNode(name, config) {}
    static PortsList providedPorts()
    {
        return {InputPort<std::string>("vehicle_id"),
                InputPort<std::string>("restricted_zone_list")};
    }
    NodeStatus tick() override { return NodeStatus::SUCCESS; }
};

class GoToArea : public StatefulActionNode
{
public:
    GoToArea(const std::string &name, const NodeConfig &config)
        : StatefulActionNode(name, config), done_(false) {}
    static PortsList providedPorts()
    {
        return {InputPort<std::string>("vehicle_id"),
                InputPort<std::string>("area_id")};
    }
    NodeStatus onStart() override
    {
        done_ = false;
        std::cout << "[GoToArea] start\n";
        return NodeStatus::RUNNING;
    }
    NodeStatus onRunning() override
    {
        done_ = true;
        return done_ ? NodeStatus::SUCCESS : NodeStatus::RUNNING;
    }
    void onHalted() override {}

private:
    bool done_;
};

class SearchArea : public StatefulActionNode
{
public:
    SearchArea(const std::string &name, const NodeConfig &config)
        : StatefulActionNode(name, config), count_(0) {}
    static PortsList providedPorts()
    {
        return {InputPort<std::string>("vehicle_id"),
                InputPort<std::string>("area_id"),
                InputPort<std::string>("pattern"),
                InputPort<std::string>("sensor_mode")};
    }
    NodeStatus onStart() override
    {
        count_ = 0;
        std::cout << "[SearchArea] start\n";
        return NodeStatus::RUNNING;
    }
    NodeStatus onRunning() override
    {
        count_++;
        return (count_ > 2) ? NodeStatus::SUCCESS : NodeStatus::RUNNING;
    }
    void onHalted() override {}

private:
    int count_;
};

class TargetDetected : public SyncActionNode
{
public:
    TargetDetected(const std::string &name, const NodeConfig &config)
        : SyncActionNode(name, config) {}
    static PortsList providedPorts()
    {
        return {InputPort<std::string>("source_vehicle"),
                OutputPort<std::string>("target_id")};
    }
    NodeStatus tick() override
    {
        setOutput("target_id", "target_001");
        std::cout << "[TargetDetected] target_001\n";
        return NodeStatus::SUCCESS;
    }
};

class HandoffTarget : public SyncActionNode
{
public:
    HandoffTarget(const std::string &name, const NodeConfig &config)
        : SyncActionNode(name, config) {}
    static PortsList providedPorts()
    {
        return {InputPort<std::string>("vehicle_id"),
                InputPort<std::string>("target_id")};
    }
    NodeStatus tick() override { return NodeStatus::SUCCESS; }
};

class TargetAssigned : public SyncActionNode
{
public:
    TargetAssigned(const std::string &name, const NodeConfig &config)
        : SyncActionNode(name, config) {}
    static PortsList providedPorts()
    {
        return {InputPort<std::string>("vehicle_id"),
                InputPort<std::string>("target_id")};
    }
    NodeStatus tick() override { return NodeStatus::SUCCESS; }
};

class TrackTarget : public StatefulActionNode
{
public:
    TrackTarget(const std::string &name, const NodeConfig &config)
        : StatefulActionNode(name, config), count_(0) {}
    static PortsList providedPorts()
    {
        return {InputPort<std::string>("vehicle_id"),
                InputPort<std::string>("target_id")};
    }
    NodeStatus onStart() override
    {
        count_ = 0;
        return NodeStatus::RUNNING;
    }
    NodeStatus onRunning() override
    {
        count_++;
        return (count_ > 2) ? NodeStatus::SUCCESS : NodeStatus::RUNNING;
    }
    void onHalted() override {}

private:
    int count_;
};

class TrackStable : public SyncActionNode
{
public:
    TrackStable(const std::string &name, const NodeConfig &config)
        : SyncActionNode(name, config) {}
    static PortsList providedPorts()
    {
        return {InputPort<std::string>("vehicle_id"),
                InputPort<std::string>("target_id")};
    }
    NodeStatus tick() override { return NodeStatus::SUCCESS; }
};

class EncircleTarget : public StatefulActionNode
{
public:
    EncircleTarget(const std::string &name, const NodeConfig &config)
        : StatefulActionNode(name, config), count_(0) {}
    static PortsList providedPorts()
    {
        return {InputPort<std::string>("vehicle_id"),
                InputPort<std::string>("target_id"),
                InputPort<double>("radius_m"),
                InputPort<double>("standoff_m")};
    }
    NodeStatus onStart() override
    {
        count_ = 0;
        return NodeStatus::RUNNING;
    }
    NodeStatus onRunning() override
    {
        count_++;
        return (count_ > 2) ? NodeStatus::SUCCESS : NodeStatus::RUNNING;
    }
    void onHalted() override {}

private:
    int count_;
};

class ReturnHome : public SyncActionNode
{
public:
    ReturnHome(const std::string &name, const NodeConfig &config)
        : SyncActionNode(name, config) {}
    static PortsList providedPorts()
    {
        return {InputPort<std::string>("vehicle_id")};
    }
    NodeStatus tick() override
    {
        std::cout << "[ReturnHome]\n";
        return NodeStatus::SUCCESS;
    }
};

void RegisterBasicNodes(BT::BehaviorTreeFactory &factory)
{
    factory.registerNodeType<BatteryOK>("BatteryOK");
    factory.registerNodeType<WithinGeofence>("WithinGeofence");
    factory.registerNodeType<OutsideRestrictedZone>("OutsideRestrictedZone");
    factory.registerNodeType<GoToArea>("GoToArea");
    factory.registerNodeType<SearchArea>("SearchArea");
    factory.registerNodeType<TargetDetected>("TargetDetected");
    factory.registerNodeType<HandoffTarget>("HandoffTarget");
    factory.registerNodeType<TargetAssigned>("TargetAssigned");
    factory.registerNodeType<TrackTarget>("TrackTarget");
    factory.registerNodeType<TrackStable>("TrackStable");
    factory.registerNodeType<EncircleTarget>("EncircleTarget");
    factory.registerNodeType<ReturnHome>("ReturnHome");
}