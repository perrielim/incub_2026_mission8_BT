#include <behaviortree_cpp/action_node.h>
#include <behaviortree_cpp/bt_factory.h>
#include <behaviortree_cpp/condition_node.h>

#include <iostream>
#include <string>

using namespace BT;

// -----------------------------------------------------------------------------
// CLEAN VARIADIC MACROS (FIXED)
// -----------------------------------------------------------------------------

#define DEFINE_SYNC_ACTION_NODE(CLASS_NAME, ...)                                  \
class CLASS_NAME : public SyncActionNode                                          \
{                                                                                 \
public:                                                                           \
    CLASS_NAME(const std::string& name, const NodeConfig& config)                 \
        : SyncActionNode(name, config) {}                                         \
    static PortsList providedPorts()                                              \
    {                                                                             \
        return { __VA_ARGS__ };                                                   \
    }                                                                             \
    NodeStatus tick() override                                                    \
    {                                                                             \
        std::cout << "[" #CLASS_NAME "]\n";                                       \
        return NodeStatus::SUCCESS;                                               \
    }                                                                             \
};

#define DEFINE_CONDITION_NODE(CLASS_NAME, ...)                                    \
class CLASS_NAME : public ConditionNode                                           \
{                                                                                 \
public:                                                                           \
    CLASS_NAME(const std::string& name, const NodeConfig& config)                 \
        : ConditionNode(name, config) {}                                          \
    static PortsList providedPorts()                                              \
    {                                                                             \
        return { __VA_ARGS__ };                                                   \
    }                                                                             \
    NodeStatus tick() override                                                    \
    {                                                                             \
        std::cout << "[" #CLASS_NAME "]\n";                                       \
        return NodeStatus::SUCCESS;                                               \
    }                                                                             \
};

#define DEFINE_STATEFUL_ACTION_NODE(CLASS_NAME, ...)                              \
class CLASS_NAME : public StatefulActionNode                                      \
{                                                                                 \
public:                                                                           \
    CLASS_NAME(const std::string& name, const NodeConfig& config)                 \
        : StatefulActionNode(name, config), count_(0) {}                          \
    static PortsList providedPorts()                                              \
    {                                                                             \
        return { __VA_ARGS__ };                                                   \
    }                                                                             \
    NodeStatus onStart() override                                                 \
    {                                                                             \
        count_ = 0;                                                               \
        std::cout << "[" #CLASS_NAME "] start\n";                                 \
        return NodeStatus::RUNNING;                                               \
    }                                                                             \
    NodeStatus onRunning() override                                               \
    {                                                                             \
        ++count_;                                                                 \
        return (count_ > 2) ? NodeStatus::SUCCESS : NodeStatus::RUNNING;           \
    }                                                                             \
    void onHalted() override {}                                                   \
private:                                                                          \
    int count_;                                                                   \
};

// -----------------------------------------------------------------------------
// Mission
// -----------------------------------------------------------------------------

DEFINE_SYNC_ACTION_NODE(mission_GetPolygonCentroid,
    InputPort<std::string>("polygon"),
    OutputPort<std::string>("centroid")
)

DEFINE_SYNC_ACTION_NODE(mission_LLAToPose,
    InputPort<std::string>("lla"),
    OutputPort<std::string>("pose")
)

DEFINE_SYNC_ACTION_NODE(mission_OverridePoseAltitude,
    InputPort<std::string>("pose"),
    InputPort<double>("altitude"),
    OutputPort<std::string>("pose_out")
)

DEFINE_SYNC_ACTION_NODE(mission_PointToPoseStamped,
    InputPort<std::string>("point"),
    OutputPort<std::string>("pose_stamped")
)

DEFINE_SYNC_ACTION_NODE(mission_SetAgentTask,
    InputPort<std::string>("agent_id"),
    InputPort<std::string>("task")
)

DEFINE_SYNC_ACTION_NODE(mission_SetTeamTask,
    InputPort<std::string>("team_id"),
    InputPort<std::string>("task")
)

DEFINE_CONDITION_NODE(mission_IsAgentInArea,
    InputPort<std::string>("agent_id"),
    InputPort<std::string>("area")
)

DEFINE_CONDITION_NODE(mission_IsAgentTask,
    InputPort<std::string>("agent_id"),
    InputPort<std::string>("task")
)

// -----------------------------------------------------------------------------
// controller
// -----------------------------------------------------------------------------

DEFINE_SYNC_ACTION_NODE(controller_CommandArm,
    InputPort<std::string>("agent_id")
)

DEFINE_SYNC_ACTION_NODE(controller_CommandLand,
    InputPort<std::string>("agent_id")
)

DEFINE_SYNC_ACTION_NODE(controller_CommandTakeOff,
    InputPort<std::string>("agent_id"),
    InputPort<double>("altitude")
)

DEFINE_SYNC_ACTION_NODE(controller_SetHome,
    InputPort<std::string>("agent_id"),
    InputPort<std::string>("home_pose")
)

DEFINE_SYNC_ACTION_NODE(controller_SetMode,
    InputPort<std::string>("agent_id"),
    InputPort<std::string>("mode")
)

DEFINE_SYNC_ACTION_NODE(controller_SetPointLocal,
    InputPort<std::string>("agent_id"),
    InputPort<std::string>("pose")
)

DEFINE_CONDITION_NODE(controller_BatteryOK,
    InputPort<std::string>("agent_id"),
    InputPort<double>("min_battery_pct")
)

DEFINE_CONDITION_NODE(controller_StateOK,
    InputPort<std::string>("agent_id")
)

// -----------------------------------------------------------------------------
// Navigation
// -----------------------------------------------------------------------------

DEFINE_STATEFUL_ACTION_NODE(navigation_NavigateToPose,
    InputPort<std::string>("agent_id"),
    InputPort<std::string>("pose")
)

// -----------------------------------------------------------------------------
// Exploration
// -----------------------------------------------------------------------------

DEFINE_SYNC_ACTION_NODE(exploration_AssignPartitions,
    InputPort<std::string>("agents"),
    InputPort<std::string>("partitions"),
    OutputPort<std::string>("assignments")
)

DEFINE_SYNC_ACTION_NODE(exploration_DeconflictAssignments,
    InputPort<std::string>("assignments"),
    OutputPort<std::string>("assignments_out")
)

DEFINE_SYNC_ACTION_NODE(exploration_FindIngressPoint,
    InputPort<std::string>("polygon"),
    OutputPort<std::string>("ingress_point")
)

DEFINE_SYNC_ACTION_NODE(exploration_GetAgentAssignedPartitionId,
    InputPort<std::string>("agent_id"),
    InputPort<std::string>("assignments"),
    OutputPort<std::string>("partition_id")
)

DEFINE_SYNC_ACTION_NODE(exploration_GetPartitionPolygon,
    InputPort<std::string>("partitions"),
    InputPort<std::string>("partition_id"),
    OutputPort<std::string>("polygon")
)

DEFINE_SYNC_ACTION_NODE(exploration_GetSearchArea,
    InputPort<std::string>("mission_area"),
    OutputPort<std::string>("search_area")
)

DEFINE_SYNC_ACTION_NODE(exploration_PartitionSearchArea,
    InputPort<std::string>("search_area"),
    OutputPort<std::string>("partitions")
)

DEFINE_SYNC_ACTION_NODE(exploration_PlanNextViewpoint,
    InputPort<std::string>("polygon"),
    InputPort<std::string>("agent_id"),
    OutputPort<std::string>("viewpoint")
)

DEFINE_SYNC_ACTION_NODE(exploration_SetAgentExplorationStatus,
    InputPort<std::string>("agent_id"),
    InputPort<std::string>("status")
)

DEFINE_SYNC_ACTION_NODE(exploration_SetPartitionAssignments,
    InputPort<std::string>("assignments")
)

DEFINE_SYNC_ACTION_NODE(exploration_SetPartitionCompletion,
    InputPort<std::string>("partition_id"),
    InputPort<bool>("complete")
)

DEFINE_SYNC_ACTION_NODE(exploration_SetPartitions,
    InputPort<std::string>("partitions")
)

DEFINE_CONDITION_NODE(exploration_IsAllPartitionsComplete,
    InputPort<std::string>("partitions")
)

DEFINE_CONDITION_NODE(exploration_IsPartitionComplete,
    InputPort<std::string>("partition_id")
)

DEFINE_CONDITION_NODE(exploration_IsPartitionSet,
    InputPort<std::string>("partition_id")
)

// -----------------------------------------------------------------------------
// Transitional (keep for now)
// -----------------------------------------------------------------------------

DEFINE_SYNC_ACTION_NODE(TargetDetected,
    InputPort<std::string>("source_vehicle"),
    OutputPort<std::string>("target_id")
)

DEFINE_SYNC_ACTION_NODE(HandoffTarget,
    InputPort<std::string>("vehicle_id"),
    InputPort<std::string>("target_id")
)

DEFINE_SYNC_ACTION_NODE(TargetAssigned,
    InputPort<std::string>("vehicle_id"),
    InputPort<std::string>("target_id")
)

DEFINE_STATEFUL_ACTION_NODE(TrackTarget,
    InputPort<std::string>("vehicle_id"),
    InputPort<std::string>("target_id")
)

DEFINE_CONDITION_NODE(TrackStable,
    InputPort<std::string>("vehicle_id"),
    InputPort<std::string>("target_id")
)

DEFINE_STATEFUL_ACTION_NODE(EncircleTarget,
    InputPort<std::string>("vehicle_id"),
    InputPort<std::string>("target_id"),
    InputPort<double>("radius_m"),
    InputPort<double>("standoff_m")
)

// -----------------------------------------------------------------------------
// Registration
// -----------------------------------------------------------------------------

void RegisterAllNodes(BT::BehaviorTreeFactory& factory)
{
    factory.registerNodeType<mission_GetPolygonCentroid>("mission_GetPolygonCentroid");
    factory.registerNodeType<mission_LLAToPose>("mission_LLAToPose");
    factory.registerNodeType<mission_OverridePoseAltitude>("mission_OverridePoseAltitude");
    factory.registerNodeType<mission_PointToPoseStamped>("mission_PointToPoseStamped");
    factory.registerNodeType<mission_SetAgentTask>("mission_SetAgentTask");
    factory.registerNodeType<mission_SetTeamTask>("mission_SetTeamTask");
    factory.registerNodeType<mission_IsAgentInArea>("mission_IsAgentInArea");
    factory.registerNodeType<mission_IsAgentTask>("mission_IsAgentTask");

    factory.registerNodeType<controller_CommandArm>("controller_CommandArm");
    factory.registerNodeType<controller_CommandLand>("controller_CommandLand");
    factory.registerNodeType<controller_CommandTakeOff>("controller_CommandTakeOff");
    factory.registerNodeType<controller_SetHome>("controller_SetHome");
    factory.registerNodeType<controller_SetMode>("controller_SetMode");
    factory.registerNodeType<controller_SetPointLocal>("controller_SetPointLocal");
    factory.registerNodeType<controller_BatteryOK>("controller_BatteryOK");
    factory.registerNodeType<controller_StateOK>("controller_StateOK");

    factory.registerNodeType<navigation_NavigateToPose>("navigation_NavigateToPose");

    factory.registerNodeType<exploration_AssignPartitions>("exploration_AssignPartitions");
    factory.registerNodeType<exploration_DeconflictAssignments>("exploration_DeconflictAssignments");
    factory.registerNodeType<exploration_FindIngressPoint>("exploration_FindIngressPoint");
    factory.registerNodeType<exploration_GetAgentAssignedPartitionId>("exploration_GetAgentAssignedPartitionId");
    factory.registerNodeType<exploration_GetPartitionPolygon>("exploration_GetPartitionPolygon");
    factory.registerNodeType<exploration_GetSearchArea>("exploration_GetSearchArea");
    factory.registerNodeType<exploration_PartitionSearchArea>("exploration_PartitionSearchArea");
    factory.registerNodeType<exploration_PlanNextViewpoint>("exploration_PlanNextViewpoint");
    factory.registerNodeType<exploration_SetAgentExplorationStatus>("exploration_SetAgentExplorationStatus");
    factory.registerNodeType<exploration_SetPartitionAssignments>("exploration_SetPartitionAssignments");
    factory.registerNodeType<exploration_SetPartitionCompletion>("exploration_SetPartitionCompletion");
    factory.registerNodeType<exploration_SetPartitions>("exploration_SetPartitions");
    factory.registerNodeType<exploration_IsAllPartitionsComplete>("exploration_IsAllPartitionsComplete");
    factory.registerNodeType<exploration_IsPartitionComplete>("exploration_IsPartitionComplete");
    factory.registerNodeType<exploration_IsPartitionSet>("exploration_IsPartitionSet");

    factory.registerNodeType<TargetDetected>("TargetDetected");
    factory.registerNodeType<HandoffTarget>("HandoffTarget");
    factory.registerNodeType<TargetAssigned>("TargetAssigned");
    factory.registerNodeType<TrackTarget>("TrackTarget");
    factory.registerNodeType<TrackStable>("TrackStable");
    factory.registerNodeType<EncircleTarget>("EncircleTarget");
}